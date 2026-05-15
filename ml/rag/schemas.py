"""
EnterpriseIQ ML — RAG Engine
Pydantic schemas for the RAG service API (internal + external contracts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Inbound ──────────────────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    chunks: list[str] = Field(..., min_length=1, max_length=500)
    corpus_id: str
    chunk_ids: list[str]


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    corpus_id: str
    top_k: int = Field(default=5, ge=1, le=20)
    use_hybrid: bool = True
    session_id: str | None = None  # for conversational RAG


# ── Outbound ─────────────────────────────────────────────────────────────────

class Source(BaseModel):
    chunk_id: str
    doc_id: str
    text_snippet: str
    page_number: int | None
    score: float


class RAGResponse(BaseModel):
    answer: str
    sources: list[Source]
    confidence: float
    model_used: str
    latency_ms: int
    session_id: str | None = None


class EmbedResponse(BaseModel):
    chunk_ids: list[str]
    embedding_count: int
    model: str


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
