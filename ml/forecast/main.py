"""
EnterpriseIQ ML — Forecasting FastAPI Service
Internal: POST /internal/forecast/run, GET /internal/forecast/results/{forecast_id}
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
from forecast.forecaster import ForecastingSystem, ForecastResult

configure_logging("ml-forecast-service")
logger = structlog.get_logger(__name__)


class ForecastRequest(BaseModel):
    dataset_id: str
    table: str
    target_column: str
    horizon_days: int = Field(default=30, ge=1, le=365)
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)
    force_model: Literal["prophet", "automl"] | None = None


class PredictionPoint(BaseModel):
    ds: str
    yhat: float
    yhat_lower: float
    yhat_upper: float
    is_forecast: bool


class ForecastResponse(BaseModel):
    forecast_id: str
    dataset_id: str
    target_column: str
    model_used: str
    horizon_days: int
    predictions: list[PredictionPoint]
    metrics: dict[str, float]
    explanation: str
    changepoints: list[str]
    forecast_start_date: str | None
    generated_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Forecast service starting up")
    app.state.forecaster = ForecastingSystem()
    yield


app = FastAPI(
    title="EnterpriseIQ Forecasting Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="ml-forecast-service")


@app.post("/internal/forecast/run", response_model=ForecastResponse)
async def run_forecast(req: ForecastRequest):
    try:
        forecaster: ForecastingSystem = app.state.forecaster
        result: ForecastResult = forecaster.run(
            dataset_id=req.dataset_id,
            table=req.table,
            target_col=req.target_column,
            horizon=req.horizon_days,
            confidence_level=req.confidence_level,
            force_model=req.force_model,
        )

        return ForecastResponse(
            forecast_id=result.forecast_id,
            dataset_id=result.dataset_id,
            target_column=result.target_column,
            model_used=result.model_used,
            horizon_days=result.horizon_days,
            predictions=[PredictionPoint(**p) for p in result.predictions],
            metrics=result.metrics,
            explanation=result.explanation,
            changepoints=result.changepoints,
            forecast_start_date=result.forecast_start_date,
            generated_at=result.generated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Forecast failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
