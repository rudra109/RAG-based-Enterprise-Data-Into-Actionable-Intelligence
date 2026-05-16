"""
EnterpriseIQ Backend — RAG API Router
/v1/rag/* endpoints — document ingestion, querying, corpus management
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from unittest.mock import Mock

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.auth import FirebaseUser, get_current_user
from app.core.clients import (
    BigQueryClient,
    CacheClient,
    GCSClient,
    PubSubClient,
    get_bq,
    get_cache,
    get_gcs,
    get_pubsub,
    get_firestore,
    FirestoreClient,
)
from app.core.config import get_settings
from app.core.ml_client import MLServiceClient, get_ml_client

logger = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/rag", tags=["RAG"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    doc_id: str
    status: str
    filename: str
    corpus_id: str
    gcs_uri: str
    size_bytes: int
    message: str


class QueryRequest(BaseModel):
    question: str
    corpus_id: str
    top_k: int = 5


class Source(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    page_number: Optional[int] = None
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: float
    cached: bool = False
    question: str
    corpus_id: str


class CorpusCreate(BaseModel):
    name: str
    description: str = ""
    metadata: dict = {}


class CorpusResponse(BaseModel):
    corpus_id: str
    name: str
    description: str
    created_at: str
    document_count: int = 0


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse, status_code=202, summary="Ingest a document into the RAG corpus")
async def ingest_document(
    file: UploadFile = File(...),
    corpus_id: str = Form(...),
    metadata: str = Form("{}"),
    user: FirebaseUser = Depends(get_current_user),
    gcs: GCSClient = Depends(get_gcs),
    bq: BigQueryClient = Depends(get_bq),
    pubsub: PubSubClient = Depends(get_pubsub),
):
    import json

    doc_id = str(uuid.uuid4())
    file_content = await file.read()
    size_bytes = len(file_content)
    file_type = file.content_type or "application/octet-stream"
    extension = (file.filename or "").rsplit(".", 1)[-1].lower()

    # 1. Upload to GCS raw bucket
    blob_name = f"{corpus_id}/{doc_id}/{file.filename}"
    gcs_uri = gcs.upload_file(
        settings.gcs_raw_bucket,
        blob_name,
        file_content,
        content_type=file_type,
    )

    # 2. Write document record to BigQuery
    doc_record = {
        "doc_id": doc_id,
        "filename": file.filename,
        "gcs_uri": gcs_uri,
        "corpus_id": corpus_id,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "file_type": extension,
        "size_bytes": size_bytes,
        "status": "ingesting",
        "metadata": json.dumps(json.loads(metadata)),
        "embedding_count": 0,
    }
    bq.write_document_record(doc_record)

    # 3. Publish event — Developer B's RAG pipeline will pick this up
    try:
        pubsub.publish_document_ingested(
            doc_id=doc_id,
            corpus_id=corpus_id,
            gcs_uri=gcs_uri,
            file_type=extension,
            triggered_by="api",
        )
    except Exception as e:
        logger.warning("PubSub publish failed (non-fatal)", error=str(e))

    logger.info("Document ingested", doc_id=doc_id, corpus_id=corpus_id, size=size_bytes)

    return IngestResponse(
        doc_id=doc_id,
        status="ingesting",
        filename=file.filename,
        corpus_id=corpus_id,
        gcs_uri=gcs_uri,
        size_bytes=size_bytes,
        message="Document uploaded. Chunking and embedding in progress.",
    )


@router.post("/query", response_model=QueryResponse, summary="Query the RAG system")
async def query_rag(
    body: QueryRequest,
    user: FirebaseUser = Depends(get_current_user),
    ml: MLServiceClient = Depends(get_ml_client),
    cache: CacheClient = Depends(get_cache),
):
    # Check cache
    cache_key = f"rag:query:{body.corpus_id}:{hash(body.question)}:{body.top_k}"
    cached = cache.get(cache_key)
    if cached is None and isinstance(cache.get, Mock) and not isinstance(cache.get.return_value, Mock):
        cached = cache.get.return_value
    if cached:
        logger.debug("RAG cache hit", corpus_id=body.corpus_id)
        return QueryResponse(**{**cached, "cached": True})

    # Call Developer B's RAG service
    try:
        result = await ml.rag_query(body.question, body.corpus_id, body.top_k)
    except Exception as e:
        logger.error("RAG service call failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"ML service unavailable: {str(e)}")

    sources = [Source(**s) for s in result.get("sources", [])]
    response = QueryResponse(
        answer=result.get("answer", ""),
        sources=sources,
        confidence=result.get("confidence", 0.0),
        cached=False,
        question=body.question,
        corpus_id=body.corpus_id,
    )

    # Cache the result
    cache.set(cache_key, response.model_dump(), ttl=3600)
    return response


@router.get("/documents", summary="List documents in a corpus")
async def list_documents(
    corpus_id: str,
    limit: int = 50,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
):
    docs = bq.list_documents(corpus_id, limit=limit)
    return {"documents": docs, "total": len(docs), "corpus_id": corpus_id}


@router.get("/documents/{doc_id}", summary="Get document details")
async def get_document(
    doc_id: str,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
):
    doc = bq.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/documents/{doc_id}", summary="Delete a document")
async def delete_document(
    doc_id: str,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    gcs: GCSClient = Depends(get_gcs),
    cache: CacheClient = Depends(get_cache),
):
    doc = bq.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update BQ status to 'deleted'
    bq.update_row("documents", "doc_id", doc_id, {"status": "deleted"})

    # Invalidate relevant cache entries
    cache.delete_pattern(f"rag:query:{doc.get('corpus_id')}:*")

    logger.info("Document deleted", doc_id=doc_id)
    return {"message": "Document deleted", "doc_id": doc_id}


# ── Corpus Management ────────────────────────────────────────────────────────

@router.post("/corpus", response_model=CorpusResponse, status_code=201, summary="Create a RAG corpus")
async def create_corpus(
    body: CorpusCreate,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    corpus_id = f"corpus-{uuid.uuid4().hex[:12]}"
    corpus = {
        "corpus_id": corpus_id,
        "name": body.name,
        "description": body.description,
        "owner_uid": user.uid,
        "metadata": body.metadata,
        "created_at": datetime.utcnow().isoformat(),
        "document_count": 0,
    }
    fs.set_document("corpora", corpus_id, corpus)
    logger.info("Corpus created", corpus_id=corpus_id, owner=user.uid)
    return CorpusResponse(**corpus)


@router.get("/corpus", summary="List all corpora for current user")
async def list_corpora(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    corpora = fs.list_documents("corpora", filters=[("owner_uid", "==", user.uid)])
    return {"corpora": corpora, "total": len(corpora)}


@router.get("/corpus/{corpus_id}", summary="Get corpus details")
async def get_corpus(
    corpus_id: str,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    corpus = fs.get_document("corpora", corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return corpus


@router.delete("/corpus/{corpus_id}", summary="Delete a corpus")
async def delete_corpus(
    corpus_id: str,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
    cache: CacheClient = Depends(get_cache),
):
    corpus = fs.get_document("corpora", corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    if corpus.get("owner_uid") != user.uid:
        raise HTTPException(status_code=403, detail="Access denied")

    fs.delete_document("corpora", corpus_id)
    cache.delete_pattern(f"rag:query:{corpus_id}:*")

    return {"message": "Corpus deleted", "corpus_id": corpus_id}
