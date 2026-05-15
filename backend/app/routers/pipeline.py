"""
EnterpriseIQ Backend — Data Pipeline Router
/v1/pipeline/* endpoints — create, trigger, monitor pipelines
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.core.auth import FirebaseUser, get_current_user
from app.core.clients import (
    BigQueryClient,
    FirestoreClient,
    PubSubClient,
    get_bq,
    get_firestore,
    get_pubsub,
)
from app.core.config import get_settings
from app.services.pipeline_service import PipelineService, get_pipeline_service

logger = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/pipeline", tags=["Pipeline"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class PipelineCreate(BaseModel):
    name: str
    pipeline_type: str  # document_ingestion | data_validator | multi_source
    description: str = ""
    schedule: Optional[str] = None  # cron expression
    config: dict = {}


class PipelineResponse(BaseModel):
    pipeline_id: str
    name: str
    pipeline_type: str
    description: str
    status: str
    schedule: Optional[str]
    created_at: str
    last_run_id: Optional[str] = None


class PipelineTriggerResponse(BaseModel):
    run_id: str
    pipeline_id: str
    status: str
    started_at: str
    message: str


class PipelineRunStats(BaseModel):
    run_id: str
    pipeline_id: str
    pipeline_name: str
    status: str
    started_at: str
    completed_at: Optional[str]
    records_processed: int
    records_failed: int
    error_message: Optional[str]
    duration_seconds: Optional[float]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=PipelineResponse, status_code=201, summary="Create a new pipeline")
async def create_pipeline(
    body: PipelineCreate,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    pipeline_id = f"pipeline-{uuid.uuid4().hex[:12]}"
    pipeline = {
        "pipeline_id": pipeline_id,
        "name": body.name,
        "pipeline_type": body.pipeline_type,
        "description": body.description,
        "status": "active",
        "schedule": body.schedule,
        "config": body.config,
        "owner_uid": user.uid,
        "created_at": datetime.utcnow().isoformat(),
        "last_run_id": None,
    }
    fs.set_document("pipelines", pipeline_id, pipeline)
    logger.info("Pipeline created", pipeline_id=pipeline_id, type=body.pipeline_type)
    return PipelineResponse(**pipeline)


@router.get("", summary="List all pipelines")
async def list_pipelines(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    pipelines = fs.list_documents("pipelines", filters=[("owner_uid", "==", user.uid)])
    return {"pipelines": pipelines, "total": len(pipelines)}


@router.get("/{pipeline_id}/status", response_model=PipelineRunStats, summary="Get pipeline latest run status")
async def get_pipeline_status(
    pipeline_id: str,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    fs: FirestoreClient = Depends(get_firestore),
):
    pipeline = fs.get_document("pipelines", pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Get latest run from BigQuery
    sql = f"""
        SELECT run_id, pipeline_id, pipeline_name, status, started_at,
               completed_at, records_processed, records_failed, error_message,
               TIMESTAMP_DIFF(completed_at, started_at, SECOND) AS duration_seconds
        FROM `{bq._ref("pipeline_runs")}`
        WHERE pipeline_id = @pipeline_id
        ORDER BY started_at DESC
        LIMIT 1
    """
    rows = bq.query(sql, params=[__import__("google.cloud.bigquery", fromlist=["bigquery"]).bigquery.ScalarQueryParameter("pipeline_id", "STRING", pipeline_id)])

    if not rows:
        raise HTTPException(status_code=404, detail="No runs found for this pipeline")

    return PipelineRunStats(**rows[0])


@router.post("/{pipeline_id}/trigger", response_model=PipelineTriggerResponse, summary="Manually trigger a pipeline run")
async def trigger_pipeline(
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
    svc: PipelineService = Depends(get_pipeline_service),
):
    pipeline = fs.get_document("pipelines", pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.get("owner_uid") != user.uid:
        raise HTTPException(status_code=403, detail="Access denied")

    run_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat()

    # Run pipeline in background
    background_tasks.add_task(
        svc.execute_pipeline,
        pipeline_id=pipeline_id,
        run_id=run_id,
        pipeline_config=pipeline,
    )

    # Update last_run_id in Firestore
    fs.update_document("pipelines", pipeline_id, {"last_run_id": run_id})

    logger.info("Pipeline triggered", pipeline_id=pipeline_id, run_id=run_id)

    return PipelineTriggerResponse(
        run_id=run_id,
        pipeline_id=pipeline_id,
        status="running",
        started_at=started_at,
        message="Pipeline execution started in background",
    )


@router.get("/{pipeline_id}/runs", summary="List all runs for a pipeline")
async def list_pipeline_runs(
    pipeline_id: str,
    limit: int = 20,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
):
    from google.cloud import bigquery
    sql = f"""
        SELECT run_id, pipeline_id, pipeline_name, status, started_at,
               completed_at, records_processed, records_failed, error_message
        FROM `{bq._ref("pipeline_runs")}`
        WHERE pipeline_id = @pipeline_id
        ORDER BY started_at DESC
        LIMIT {limit}
    """
    rows = bq.query(sql, params=[bigquery.ScalarQueryParameter("pipeline_id", "STRING", pipeline_id)])
    return {"runs": rows, "total": len(rows), "pipeline_id": pipeline_id}


@router.delete("/{pipeline_id}", summary="Delete a pipeline")
async def delete_pipeline(
    pipeline_id: str,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    pipeline = fs.get_document("pipelines", pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.get("owner_uid") != user.uid:
        raise HTTPException(status_code=403, detail="Access denied")
    fs.delete_document("pipelines", pipeline_id)
    return {"message": "Pipeline deleted", "pipeline_id": pipeline_id}
