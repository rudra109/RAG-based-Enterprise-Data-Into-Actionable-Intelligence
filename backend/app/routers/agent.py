"""
EnterpriseIQ Backend — Analytics Agent Router
/v1/agent/* endpoints — NL-to-SQL queries, dataset registry
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import FirebaseUser, get_current_user
from app.core.clients import (
    BigQueryClient,
    CacheClient,
    FirestoreClient,
    get_bq,
    get_cache,
    get_firestore,
)
from app.core.ml_client import MLServiceClient, get_ml_client

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/agent", tags=["Analytics Agent"])

# Allowed SQL patterns (whitelist only SELECT)
_FORBIDDEN_SQL_PATTERNS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bTRUNCATE\b", r"\bINSERT\b",
    r"\bUPDATE\b", r"\bCREATE\b", r"\bALTER\b", r"\bEXEC\b",
    r"\bGRANT\b", r"\bREVOKE\b",
]


# ── Schemas ──────────────────────────────────────────────────────────────────

class AgentQueryRequest(BaseModel):
    question: str
    dataset_id: str
    max_rows: int = 1000


class AgentQueryResponse(BaseModel):
    sql_generated: str
    results: list
    chart_suggestion: str  # bar | line | pie | table | scatter
    explanation: str
    row_count: int
    execution_time_ms: float
    cached: bool = False


class DatasetRegisterRequest(BaseModel):
    dataset_id: str
    display_name: str
    description: str = ""
    tables: List[str] = []
    tags: List[str] = []


class DatasetResponse(BaseModel):
    dataset_id: str
    display_name: str
    description: str
    tables: List[str]
    tags: List[str]
    registered_at: str
    schema: dict = {}


# ── SQL Safety Validator ──────────────────────────────────────────────────────

def validate_sql(sql: str) -> bool:
    """Return True only if SQL is a safe SELECT statement."""
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        return False
    for pattern in _FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, stripped):
            return False
    return True


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/query", response_model=AgentQueryResponse, summary="Natural language query over structured data")
async def agent_query(
    body: AgentQueryRequest,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    ml: MLServiceClient = Depends(get_ml_client),
    cache: CacheClient = Depends(get_cache),
):
    import time

    cache_key = f"agent:query:{body.dataset_id}:{hash(body.question)}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug("Agent query cache hit", dataset=body.dataset_id)
        return AgentQueryResponse(**cached, cached=True)

    # 1. Fetch schema from BigQuery
    try:
        schema = bq.get_table_schema(body.dataset_id)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Cannot load schema for dataset '{body.dataset_id}': {e}")

    # 2. Call Developer B's NL2SQL service
    try:
        ml_result = await ml.agent_nl2sql(body.question, schema)
    except Exception as e:
        logger.error("Agent ML service error", error=str(e))
        raise HTTPException(status_code=503, detail=f"Analytics agent unavailable: {e}")

    generated_sql = ml_result.get("sql", "")

    # 3. Safety validate the SQL
    if not validate_sql(generated_sql):
        raise HTTPException(status_code=400, detail="Generated SQL failed safety validation (only SELECT allowed)")

    # 4. Execute in BigQuery
    t0 = time.perf_counter()
    try:
        rows = bq.safe_select(generated_sql)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"SQL execution error: {e}")
    exec_ms = (time.perf_counter() - t0) * 1000

    # Limit returned rows
    rows = rows[: body.max_rows]

    response = AgentQueryResponse(
        sql_generated=generated_sql,
        results=rows,
        chart_suggestion=ml_result.get("chart_type", "table"),
        explanation=ml_result.get("explanation", ""),
        row_count=len(rows),
        execution_time_ms=round(exec_ms, 2),
        cached=False,
    )

    # Cache result (shorter TTL for analytics)
    cache.set(cache_key, response.model_dump(), ttl=600)

    logger.info("Agent query executed", dataset=body.dataset_id, rows=len(rows))
    return response


# ── Dataset Registry ──────────────────────────────────────────────────────────

@router.post("/datasets", response_model=DatasetResponse, status_code=201, summary="Register a BigQuery dataset for NL querying")
async def register_dataset(
    body: DatasetRegisterRequest,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    fs: FirestoreClient = Depends(get_firestore),
):
    # Fetch live schema
    try:
        schema = bq.get_table_schema(body.dataset_id)
    except Exception:
        schema = {}

    doc = {
        "dataset_id": body.dataset_id,
        "display_name": body.display_name,
        "description": body.description,
        "tables": body.tables or list(schema.keys()),
        "tags": body.tags,
        "registered_at": datetime.utcnow().isoformat(),
        "owner_uid": user.uid,
        "schema": schema,
    }
    fs.set_document("datasets", body.dataset_id, doc)
    logger.info("Dataset registered", dataset_id=body.dataset_id)
    return DatasetResponse(**doc)


@router.get("/datasets", summary="List registered datasets")
async def list_datasets(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    datasets = fs.list_documents("datasets", filters=[("owner_uid", "==", user.uid)])
    return {"datasets": datasets, "total": len(datasets)}


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse, summary="Get dataset details + schema")
async def get_dataset(
    dataset_id: str,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    fs: FirestoreClient = Depends(get_firestore),
):
    doc = fs.get_document("datasets", dataset_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset not registered")
    # Refresh schema
    try:
        doc["schema"] = bq.get_table_schema(dataset_id)
    except Exception:
        pass
    return DatasetResponse(**doc)


@router.delete("/datasets/{dataset_id}", summary="Unregister a dataset")
async def delete_dataset(
    dataset_id: str,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    fs.delete_document("datasets", dataset_id)
    return {"message": "Dataset unregistered", "dataset_id": dataset_id}
