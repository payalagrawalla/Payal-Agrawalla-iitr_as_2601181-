"""FastAPI deployment for the Nykaa support agent."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from crew_orchestration import build_crew, mask_pii


app = FastAPI(title="Nykaa Support Agent")
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "requests.jsonl"


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    trace_id: str
    grounded: bool
    lookup_used: bool = False


class AddDocumentRequest(BaseModel):
    topic: str
    text: str


class AddDocumentResponse(BaseModel):
    success: bool
    doc_id: str


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.perf_counter()
    trace_id = uuid.uuid4().hex
    raw_text = request.url.path
    request_body = None
    try:
        body = await request.body()
        if body:
            request_body = body.decode("utf-8", errors="ignore")
    except Exception:
        request_body = None
    payload = {"trace_id": trace_id, "timestamp": datetime.now(timezone.utc).isoformat(), "path": request.url.path, "method": request.method, "request": mask_pii(request_body or raw_text), "status_code": 200}
    try:
        response = await call_next(request)
        payload["status_code"] = response.status_code
        return response
    finally:
        payload["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    trace_id = uuid.uuid4().hex
    start = time.perf_counter()
    masked_query = mask_pii(request.query)
    crew = build_crew()
    response = crew.kickoff(masked_query)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"trace_id": trace_id, "timestamp": datetime.now(timezone.utc).isoformat(), "path": "/ask", "method": "POST", "request": mask_pii(request.query), "response": response.answer, "duration_ms": duration_ms, "grounded": response.grounded, "lookup_used": response.lookup_used}, ensure_ascii=True) + "\n")
    return AskResponse(answer=response.answer, trace_id=trace_id, grounded=response.grounded, lookup_used=response.lookup_used)


@app.post("/add-document", response_model=AddDocumentResponse)
async def add_document(payload: AddDocumentRequest) -> AddDocumentResponse:
    doc_id = f"doc_{uuid.uuid4().hex[:6]}"
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"trace_id": uuid.uuid4().hex, "timestamp": datetime.now(timezone.utc).isoformat(), "path": "/add-document", "method": "POST", "request": mask_pii(payload.text), "doc_id": doc_id}, ensure_ascii=True) + "\n")
    return AddDocumentResponse(success=True, doc_id=doc_id)


@app.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            payload = json.loads(message)
            query = payload.get("query", "")
            crew = build_crew()
            response = crew.kickoff(mask_pii(query))
            await websocket.send_text(json.dumps({"answer": response.answer, "grounded": response.grounded, "lookup_used": response.lookup_used}))
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.send_text(json.dumps({"error": "A request error occurred."}))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
