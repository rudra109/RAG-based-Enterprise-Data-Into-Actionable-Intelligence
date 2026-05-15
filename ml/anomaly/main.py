"""
EnterpriseIQ ML — Anomaly Detection FastAPI Service
Internal service: POST /internal/anomaly/detect
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, "../")

from shared.logging_setup import configure_logging
from anomaly.detector import AnomalyDetectionSystem, AnomalyReport

configure_logging("ml-anomaly-service")
logger = structlog.get_logger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class DetectRequest(BaseModel):
    dataset_id: str
    table: str
    time_column: str = "timestamp"
    metric_columns: list[str] = Field(..., min_length=1)
    sensitivity: Literal["low", "medium", "high"] = "medium"
    use_statistical: bool = True
    use_ml: bool = True
    use_semantic: bool = False  # Off by default (Gemini cost)


class AnomalyItem(BaseModel):
    anomaly_id: str
    index: int
    metric_name: str
    actual_value: float
    anomaly_score: float
    severity: str
    method: str
    reason: str


class DetectResponse(BaseModel):
    dataset_id: str
    total_records: int
    anomaly_count: int
    critical_count: int
    methods_used: list[str]
    anomalies: list[AnomalyItem]
    generated_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Anomaly service starting up")
    app.state.detector = AnomalyDetectionSystem()
    yield
    logger.info("Anomaly service shutting down")


app = FastAPI(
    title="EnterpriseIQ Anomaly Detection Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="ml-anomaly-service")


@app.post("/internal/anomaly/detect", response_model=DetectResponse)
async def detect_anomalies(req: DetectRequest):
    try:
        detector: AnomalyDetectionSystem = app.state.detector
        report: AnomalyReport = detector.detect(
            dataset_id=req.dataset_id,
            table=req.table,
            time_column=req.time_column,
            metric_columns=req.metric_columns,
            sensitivity=req.sensitivity,
            use_statistical=req.use_statistical,
            use_ml=req.use_ml,
            use_semantic=req.use_semantic,
        )

        return DetectResponse(
            dataset_id=report.dataset_id,
            total_records=report.total_records,
            anomaly_count=report.anomaly_count,
            critical_count=report.critical_count,
            methods_used=report.detection_methods_used,
            anomalies=[
                AnomalyItem(
                    anomaly_id=a.anomaly_id,
                    index=a.index,
                    metric_name=a.metric_name,
                    actual_value=a.actual_value,
                    anomaly_score=a.anomaly_score,
                    severity=a.severity,
                    method=a.method,
                    reason=a.reason,
                )
                for a in report.anomalies
            ],
            generated_at=report.generated_at,
        )
    except Exception as e:
        logger.error("Anomaly detection failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
