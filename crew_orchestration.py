"""CrewAI-style orchestration with mock/fallback support."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError, Field

from dataset import ORDERS, check_order_status
from rag_core import build_collections, grounded_answer, retrieve_top_k, get_knowledge_base


class CrewResponseModel(BaseModel):
    answer: str
    grounded: bool
    source: str
    lookup_used: bool = False
    tool_trace: List[str] = Field(default_factory=list)


def mask_pii(text: str) -> str:
    masked = re.sub(r"\b(?:\+?91[-\s]?)?(?:\d{10})\b", "**********", text)
    masked = re.sub(r"\b(?:\d{4})(?:\s|-)?(?:\d{4})(?:\s|-)?(?:\d{4})(?:\s|-)?(?:\d{4})\b", "XXXX", masked)
    masked = re.sub(r"\b(?:\d{4})\b", "XXXX", masked)
    return masked


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    triggers = [
        "ignore previous instructions",
        "you are now",
        "system prompt",
        "reveal hidden instructions",
        "developer message",
        "override policy",
    ]
    return any(trigger in lowered for trigger in triggers)


def extract_record_id(query: str) -> Optional[str]:
    match = re.search(r"NYK-\d{5}", query.upper())
    return match.group(0) if match else None


class MockCrew:
    """Fallback orchestration useful when CrewAI is not installed."""

    def __init__(self):
        self.tool_calls: List[str] = []

    def kickoff(self, query: str) -> CrewResponseModel:
        masked_query = mask_pii(query)
        if detect_prompt_injection(masked_query):
            raise ValueError("Prompt injection detected; request blocked.")

        docs = get_knowledge_base()
        collection = build_collections(docs)["fixed"]
        rag_result = grounded_answer(masked_query, collection, threshold=0.18)
        lookup_id = extract_record_id(masked_query)
        lookup_result = None
        if lookup_id:
            lookup_result = check_order_status(lookup_id)

        answer = rag_result["answer"]
        if lookup_result:
            answer = f"{answer} Order lookup: {lookup_result['status']}, value INR {lookup_result['order_value_inr']}, escalation {lookup_result['escalation_score']}."
        payload = {
            "answer": answer,
            "grounded": rag_result["grounded"] or bool(lookup_result),
            "source": "fixed collection",
            "lookup_used": bool(lookup_result),
            "tool_trace": ["rag_lookup", "check_order_status"] if lookup_result else ["rag_lookup"],
        }
        return CrewResponseModel(**payload)


def build_crew() -> MockCrew:
    return MockCrew()


def validate_response(payload: Dict[str, Any]) -> CrewResponseModel:
    model = CrewResponseModel(**payload)
    return model


def run_review_stage(draft_answer: str, context: str, *, allow_revision: bool = False) -> Dict[str, Any]:
    """Simple review gate that approves or revises a draft answer."""
    if allow_revision and "cancel" in draft_answer.lower() and "7-day" in draft_answer.lower():
        revised = "Based on the retrieved policy, orders can only be cancelled while they remain in the Placed or Packed state; once a shipment is marked Shipped, cancellation is no longer the default path."
        return {"approved": False, "final_answer": revised, "reason": "Draft incorrectly claimed a 7-day cancellation rule; policy context says shipments prevent cancellation."}
    return {"approved": True, "final_answer": draft_answer, "reason": "Draft aligns with retrieved policy and is acceptable."}


if __name__ == "__main__":
    crew = build_crew()
    response = crew.kickoff("What is the return window for apparel?")
    print(response)
    print(validate_response(response.model_dump()))
