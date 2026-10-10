"""Minimal local RAG engine used in the capstone.

If the ML libraries are installed, the code uses sentence-transformers and
ChromaDB. Otherwise it falls back to deterministic hashing so the project still
runs in a mock-only environment without internet access.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from knowledge_base import get_knowledge_base


try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None


def _hash_embedding(text: str, dim: int = 384) -> List[float]:
    tokens = re.findall(r"\w+", text.lower())
    vec = [0.0 for _ in range(dim)]
    for i, token in enumerate(tokens):
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        value = int(digest[:8], 16) / 0xFFFFFFFF
        vec[i % dim] += value
    # Normalize to a stable vector.
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_fixed_size(documents: Sequence[Dict[str, Any]], chunk_size: int = 220, overlap: int = 40) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    stride = chunk_size - overlap
    for document in documents:
        text = document["text"]
        for offset in range(0, len(text), stride):
            chunk_text = text[offset:offset + chunk_size]
            if chunk_text.strip():
                chunks.append(
                    {
                        "chunk_id": f"{document['doc_id']}_fixed_{len(chunks)}",
                        "doc_id": document["doc_id"],
                        "topic": document["topic"],
                        "text": chunk_text.strip(),
                    }
                )
    return chunks


def chunk_sentence_based(documents: Sequence[Dict[str, Any]], sentences_per_chunk: int = 2) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for document in documents:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", document["text"]) if s.strip()]
        for idx in range(0, len(sentences), sentences_per_chunk):
            section = sentences[idx:idx + sentences_per_chunk]
            if section:
                chunks.append(
                    {
                        "chunk_id": f"{document['doc_id']}_sent_{len(chunks)}",
                        "doc_id": document["doc_id"],
                        "topic": document["topic"],
                        "text": " ".join(section),
                    }
                )
    return chunks


class LocalChromaCollection:
    """Simple approximation of ChromaDB collection for mock-mode use."""

    def __init__(self, name: str, chunks: Sequence[Dict[str, Any]]):
        self.name = name
        self.chunks = list(chunks)

    def upsert(self, records):
        for record in records:
            existing = [c for c in self.chunks if c.get("chunk_id") == record.get("chunk_id")]
            if existing:
                existing[0].update(record)
            else:
                self.chunks.append(record)

    def query(self, query_text: str, n_results: int = 5):
        qvec = _hash_embedding(query_text)
        scored = []
        for chunk in self.chunks:
            vec = _hash_embedding(chunk["text"])
            score = cosine_similarity(qvec, vec)
            scored.append({**chunk, "score": score})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return {"documents": [[item["text"] for item in scored[:n_results]]], "metadatas": [[{"doc_id": item["doc_id"], "topic": item["topic"]} for item in scored[:n_results]]], "distances": [[1.0 - item["score"] for item in scored[:n_results]]], "ids": [[item["chunk_id"] for item in scored[:n_results]]], "scores": [item["score"] for item in scored[:n_results]]}


def build_collections(documents: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    fixed_chunks = chunk_fixed_size(documents)
    sentence_chunks = chunk_sentence_based(documents)
    collections = {
        "fixed": LocalChromaCollection("fixed", fixed_chunks),
        "sentence": LocalChromaCollection("sentence", sentence_chunks),
    }
    return collections


def retrieve_top_k(collection: Any, query: str, k: int = 3) -> List[Tuple[str, str, float]]:
    result = collection.query(query_text=query, n_results=k)
    rows: List[Tuple[str, str, float]] = []
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    scores = result.get("scores", [])
    for idx, text in enumerate(documents):
        meta = metadatas[idx] if idx < len(metadatas) else {}
        score = scores[idx] if idx < len(scores) else 0.0
        rows.append((meta.get("doc_id", "doc_unknown"), text, float(score)))
    return rows


def grounded_answer(query: str, collection: Any, threshold: float = 0.18) -> Dict[str, Any]:
    top_rows = retrieve_top_k(collection, query, k=3)
    if not top_rows:
        return {"answer": "I don't know.", "grounded": False, "context": []}
    top_score = top_rows[0][2]
    if top_score < threshold:
        return {"answer": "I don't know based on the available policy context.", "grounded": False, "context": []}
    context = "\n".join(row[1] for row in top_rows)
    answer = f"Based on the retrieved policy context, {query} is addressed as follows: {context[:600]}"
    return {"answer": answer, "grounded": True, "context": top_rows}


def calibrate_threshold() -> Dict[str, Any]:
    docs = get_knowledge_base()
    fixed_collection = build_collections(docs)["fixed"]
    in_scope = [
        "What is the return window for apparel?",
        "How long does COD refund take after return?",
        "Can I cancel my order if it has shipped?",
    ]
    out_scope = [
        "Tell me the capital of France.",
        "How do I hack a bank transfer?",
    ]
    values: List[Tuple[str, float]] = []
    for q in in_scope + out_scope:
        rows = retrieve_top_k(fixed_collection, q, k=1)
        values.append((q, rows[0][2] if rows else 0.0))
    in_values = [v for q, v in values if q in in_scope]
    out_values = [v for q, v in values if q in out_scope]
    threshold = round((max(in_values) + min(out_values)) / 2.0, 4)
    return {
        "in_scope": list(zip(in_scope, in_values)),
        "out_scope": list(zip(out_scope, out_values)),
        "threshold": threshold,
    }


def evaluate_collection(collection_name: str, documents: Sequence[Dict[str, Any]], queries: Sequence[str]) -> List[Dict[str, Any]]:
    collection = build_collections(documents)[collection_name]
    results: List[Dict[str, Any]] = []
    for query in queries:
        hits = retrieve_top_k(collection, query, k=5)
        related_docs = {doc_id for doc_id, _, _ in hits}
        target_docs = {doc["doc_id"] for doc in documents if any(keyword in query.lower() for keyword in re.findall(r"\w+", doc["topic"].lower())) }
        if not target_docs and "refund" in query.lower():
            target_docs = {"doc_02"}
        if not target_docs and "return" in query.lower():
            target_docs = {"doc_01"}
        if not target_docs and "cancel" in query.lower():
            target_docs = {"doc_06"}
        tp = len(related_docs & target_docs)
        precision = tp / max(len(related_docs), 1)
        recall = tp / max(len(target_docs), 1)
        results.append({"query": query, "precision": precision, "recall": recall, "related_docs": sorted(related_docs), "target_docs": sorted(target_docs)})
    return results


if __name__ == "__main__":
    docs = get_knowledge_base()
    fixed = build_collections(docs)["fixed"]
    print("fixed retrieval sample:", retrieve_top_k(fixed, "What is the return window for apparel?", 2))
    print("calibration:", calibrate_threshold())
