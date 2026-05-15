"""
EnterpriseIQ Backend — Anomaly Detection Router
/v1/anomaly/* endpoints
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import FirebaseUser, get_current_user
from app.core.clients import BigQueryClient, CacheClient, get_bq, get_cache
from app.core.ml_client import MLServiceClient, get_ml_client

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/anomaly", tags=["Anomaly Detection"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class AnomalyDetectRequest(BaseModel):
    dataset_id: str
    time_column: str
    metric_columns: List[str]
    sensitivity: str = "medium"  # low | medium | high


class AnomalyResult(BaseModel):
    anomaly_id: str
    dataset_id: str
    detected_at: str
    metric_name: str
    anomaly_score: float
    actual_value: Optional[float]
    expected_value: Optional[float]
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    is_acknowledged: bool = False
    severity: str  # low | medium | high | critical


class AnomalyDetectResponse(BaseModel):
    job_id: str
    dataset_id: str
    anomalies: List[AnomalyResult]
    total_anomalies: int
    processing_time_ms: float


class AcknowledgeRequest(BaseModel):
    anomaly_id: str
    note: str = ""


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/detect", response_model=AnomalyDetectResponse, summary="Run anomaly detection on a dataset")
async def detect_anomalies(
    body: AnomalyDetectRequest,
    user: FirebaseUser = Depends(get_current_user),
    ml: MLServiceClient = Depends(get_ml_client),
    bq: BigQueryClient = Depends(get_bq),
):
    import time
    import uuid

    t0 = time.perf_counter()

    # Call Developer B's anomaly service
    try:
        result = await ml.anomaly_detect(
            body.dataset_id,
            body.time_column,
            body.metric_columns,
            body.sensitivity,
        )
    except Exception as e:
        logger.error("Anomaly service error", error=str(e))
        raise HTTPException(status_code=503, detail=f"Anomaly service unavailable: {e}")

    anomalies_raw = result.get("anomalies", [])
    exec_ms = (time.perf_counter() - t0) * 1000

    # Persist to BigQuery
    if anomalies_raw:
        try:
            bq_rows = [
                {
                    "anomaly_id": a.get("anomaly_id", str(uuid.uuid4())),
                    "dataset_id": body.dataset_id,
                    "detected_at": datetime.utcnow().isoformat(),
                    "metric_name": a.get("metric_name", ""),
                    "anomaly_score": float(a.get("anomaly_score", 0)),
                    "actual_value": a.get("actual_value"),
                    "expected_value": a.get("expected_value"),
                    "lower_bound": a.get("lower_bound"),
                    "upper_bound": a.get("upper_bound"),
                    "is_acknowledged": False,
                    "severity": a.get("severity", "medium"),
                }
                for a in anomalies_raw
            ]
            bq.insert_rows("anomaly_results", bq_rows)
        except Exception as e:
            logger.warning("Failed to persist anomaly results to BQ", error=str(e))

    anomalies = [AnomalyResult(**a) for a in anomalies_raw]

    logger.info("Anomaly detection complete", dataset=body.dataset_id, count=len(anomalies))
    return AnomalyDetectResponse(
        job_id=result.get("job_id", str(uuid.uuid4())),
        dataset_id=body.dataset_id,
        anomalies=anomalies,
        total_anomalies=len(anomalies),
        processing_time_ms=round(exec_ms, 2),
    )


@router.get("/list", summary="List detected anomalies for a dataset")
async def list_anomalies(
    dataset_id: str,
    start_time: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    cache: CacheClient = Depends(get_cache),
):
    cache_key = f"anomaly:list:{dataset_id}:{start_time}:{severity}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    results = bq.list_anomalies(dataset_id, start_time=start_time, limit=limit)

    if severity:
        results = [r for r in results if r.get("severity") == severity]

    payload = {
        "anomalies": results,
        "total": len(results),
        "dataset_id": dataset_id,
    }
    cache.set(cache_key, payload, ttl=300)
    return payload


@router.post("/acknowledge", summary="Acknowledge an anomaly")
async def acknowledge_anomaly(
    body: AcknowledgeRequest,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    cache: CacheClient = Depends(get_cache),
):
    bq.update_row("anomaly_results", "anomaly_id", body.anomaly_id, {"is_acknowledged": "true"})
    cache.delete_pattern("anomaly:list:*")
    logger.info("Anomaly acknowledged", anomaly_id=body.anomaly_id, by=user.uid)
    return {"message": "Anomaly acknowledged", "anomaly_id": body.anomaly_id}


@router.get("/summary", summary="Get anomaly summary statistics for a dataset")
async def anomaly_summary(
    dataset_id: str,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    cache: CacheClient = Depends(get_cache),
):
    cache_key = f"anomaly:summary:{dataset_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    from google.cloud import bigquery
    sql = f"""
        SELECT
            severity,
            COUNT(*) AS count,
            AVG(anomaly_score) AS avg_score,
            MAX(detected_at) AS latest_detected
        FROM `{bq._ref("anomaly_results")}`
        WHERE dataset_id = @dataset_id AND is_acknowledged = FALSE
        GROUP BY severity
        ORDER BY count DESC
    """
    rows = bq.query(sql, [bigquery.ScalarQueryParameter("dataset_id", "STRING", dataset_id)])
    result = {"dataset_id": dataset_id, "summary": rows}
    cache.set(cache_key, result, ttl=300)
    return result
