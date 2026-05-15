"""
EnterpriseIQ ML — RAG Service FastAPI Application
Internal service (VPC-only) called by Person A's backend.

Endpoints:
  POST /internal/rag/query    → RAG query (returns RAGResponse)
  POST /internal/rag/embed    → Embed + index chunks (called post-ingestion)
  GET  /internal/rag/stream   → SSE streaming query
  GET  /health                → Health check
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add repo root to path so shared/ is importable
sys.path.insert(0, "../")

from shared.logging_setup import configure_logging
from rag.engine import EnterpriseRAGEngine
from rag.schemas import (
    EmbedRequest,
    EmbedResponse,
    HealthResponse,
    RAGQueryRequest,
    RAGResponse,
)
from rag.evaluation import RAGEvaluator

configure_logging("ml-rag-service")
logger = structlog.get_logger(__name__)


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RAG service starting up")
    app.state.engine = EnterpriseRAGEngine()
    app.state.evaluator = RAGEvaluator()
    yield
    logger.info("RAG service shutting down")


app = FastAPI(
    title="EnterpriseIQ RAG Service",
    description="Internal ML service — RAG Engine (Gemini + Vertex AI Vector Search)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # VPC-internal only; real restriction via Cloud Run IAM
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="ml-rag-service")


@app.post("/internal/rag/embed", response_model=EmbedResponse)
async def embed_and_index(req: EmbedRequest):
    """
    Called by Person A's Dataflow pipeline after document chunking.
    Embeds chunks and upserts into Vertex AI Vector Search.
    """
    if len(req.chunks) != len(req.chunk_ids):
        raise HTTPException(status_code=422, detail="chunks and chunk_ids must have equal length")

    try:
        engine: EnterpriseRAGEngine = app.state.engine
        count = engine.embed_and_index(req.chunks, req.chunk_ids, req.corpus_id)
        return EmbedResponse(
            chunk_ids=req.chunk_ids,
            embedding_count=count,
            model="text-embedding-004",
        )
    except Exception as e:
        logger.error("Embedding failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/rag/query", response_model=RAGResponse)
async def rag_query(req: RAGQueryRequest):
    """
    Main RAG query endpoint — called by Person A's /v1/rag/query proxy.
    Returns a grounded answer with source citations.
    """
    try:
        engine: EnterpriseRAGEngine = app.state.engine
        response = engine.query(
            question=req.question,
            corpus_id=req.corpus_id,
            top_k=req.top_k,
            use_hybrid=req.use_hybrid,
            session_id=req.session_id,
        )

        # Async: log RAGAS evaluation metrics to BigQuery
        asyncio.create_task(
            app.state.evaluator.log_query_async(req.question, response)
        )

        return response
    except Exception as e:
        logger.error("RAG query failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/rag/stream")
async def rag_stream(req: RAGQueryRequest):
    """
    Streaming RAG endpoint — Server-Sent Events for real-time token delivery.
    Person C's chat UI reads this via fetch streaming.
    """
    engine: EnterpriseRAGEngine = app.state.engine

    # Retrieve chunks first
    if req.use_hybrid:
        chunks = engine.hybrid_search(req.question, req.corpus_id, req.top_k)
    else:
        chunks = engine.retrieve(req.question, req.corpus_id, req.top_k)

    if chunks:
        chunks = engine.rerank(req.question, chunks)

    async def event_generator() -> AsyncGenerator[str, None]:
        async for token in engine.stream_generate(req.question, chunks, req.session_id):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
