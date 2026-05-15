"""
EnterpriseIQ Backend — Forecasting Router
/v1/forecast/* endpoints
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import FirebaseUser, get_current_user
from app.core.clients import BigQueryClient, CacheClient, get_bq, get_cache
from app.core.ml_client import MLServiceClient, get_ml_client

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/forecast", tags=["Forecasting"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ForecastRunRequest(BaseModel):
    dataset_id: str
    target_column: str
    horizon_days: int
    confidence_level: float = 0.95


class ForecastPoint(BaseModel):
    forecast_timestamp: str
    predicted_value: float
    lower_bound: float
    upper_bound: float


class ForecastRunResponse(BaseModel):
    forecast_id: str
    dataset_id: str
    target_column: str
    horizon_days: int
    status: str
    created_at: str
    points: List[ForecastPoint]
    model_version: str


class ForecastResultsResponse(BaseModel):
    forecast_id: str
    dataset_id: str
    target_column: str
    points: List[ForecastPoint]
    total_points: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/run", response_model=ForecastRunResponse, summary="Generate a forecast")
async def run_forecast(
    body: ForecastRunRequest,
    user: FirebaseUser = Depends(get_current_user),
    ml: MLServiceClient = Depends(get_ml_client),
    bq: BigQueryClient = Depends(get_bq),
):
    forecast_id = str(uuid.uuid4())

    # Call Developer B's forecasting service
    try:
        result = await ml.forecast_run(
            body.dataset_id,
            body.target_column,
            body.horizon_days,
            body.confidence_level,
        )
    except Exception as e:
        logger.error("Forecast service error", error=str(e))
        raise HTTPException(status_code=503, detail=f"Forecast service unavailable: {e}")

    points_raw = result.get("forecast", [])

    # Persist to BigQuery
    if points_raw:
        try:
            bq_rows = [
                {
                    "forecast_id": forecast_id,
                    "dataset_id": body.dataset_id,
                    "target_column": body.target_column,
                    "forecast_timestamp": p.get("ds", ""),
                    "predicted_value": float(p.get("yhat", 0)),
                    "lower_bound": float(p.get("yhat_lower", 0)),
                    "upper_bound": float(p.get("yhat_upper", 0)),
                    "confidence_level": body.confidence_level,
                    "model_version": result.get("model_version", "1.0"),
                }
                for p in points_raw
            ]
            bq.insert_rows("forecast_results", bq_rows)
        except Exception as e:
            logger.warning("Failed to persist forecast to BQ", error=str(e))

    points = [
        ForecastPoint(
            forecast_timestamp=p.get("ds", ""),
            predicted_value=float(p.get("yhat", 0)),
            lower_bound=float(p.get("yhat_lower", 0)),
            upper_bound=float(p.get("yhat_upper", 0)),
        )
        for p in points_raw
    ]

    logger.info("Forecast generated", forecast_id=forecast_id, dataset=body.dataset_id, points=len(points))

    return ForecastRunResponse(
        forecast_id=forecast_id,
        dataset_id=body.dataset_id,
        target_column=body.target_column,
        horizon_days=body.horizon_days,
        status="completed",
        created_at=datetime.utcnow().isoformat(),
        points=points,
        model_version=result.get("model_version", "1.0"),
    )


@router.get("/results", response_model=ForecastResultsResponse, summary="Get forecast results by forecast_id")
async def get_forecast_results(
    forecast_id: str,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
    cache: CacheClient = Depends(get_cache),
):
    cache_key = f"forecast:results:{forecast_id}"
    cached = cache.get(cache_key)
    if cached:
        return ForecastResultsResponse(**cached)

    rows = bq.get_forecast_results(forecast_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No forecast results found for '{forecast_id}'")

    points = [
        ForecastPoint(
            forecast_timestamp=str(r.get("forecast_timestamp", "")),
            predicted_value=float(r.get("predicted_value", 0)),
            lower_bound=float(r.get("lower_bound", 0)),
            upper_bound=float(r.get("upper_bound", 0)),
        )
        for r in rows
    ]

    response = ForecastResultsResponse(
        forecast_id=forecast_id,
        dataset_id=rows[0].get("dataset_id", ""),
        target_column=rows[0].get("target_column", ""),
        points=points,
        total_points=len(points),
    )
    cache.set(cache_key, response.model_dump(), ttl=3600)
    return response


@router.get("/history", summary="List recent forecasts for a dataset")
async def forecast_history(
    dataset_id: str,
    limit: int = 10,
    user: FirebaseUser = Depends(get_current_user),
    bq: BigQueryClient = Depends(get_bq),
):
    from google.cloud import bigquery
    sql = f"""
        SELECT DISTINCT forecast_id, dataset_id, target_column,
               MIN(forecast_timestamp) AS period_start,
               MAX(forecast_timestamp) AS period_end,
               COUNT(*) AS point_count
        FROM `{bq._ref("forecast_results")}`
        WHERE dataset_id = @dataset_id
        GROUP BY forecast_id, dataset_id, target_column
        ORDER BY period_start DESC
        LIMIT {limit}
    """
    rows = bq.query(sql, [bigquery.ScalarQueryParameter("dataset_id", "STRING", dataset_id)])
    return {"forecasts": rows, "total": len(rows), "dataset_id": dataset_id}
