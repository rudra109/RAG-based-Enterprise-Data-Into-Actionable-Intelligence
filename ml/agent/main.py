"""
EnterpriseIQ ML — Analytics Agent FastAPI Service
Internal: POST /internal/agent/nl2sql
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
from agent.analytics_agent import AnalyticsAgent, AgentResult

configure_logging("ml-agent-service")
logger = structlog.get_logger(__name__)


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    dataset_id: str
    session_id: str | None = None


class AgentQueryResponse(BaseModel):
    question: str
    sql_generated: str
    results: list[dict]
    chart_suggestion: str
    explanation: str
    row_count: int
    dataset_id: str
    query_id: str
    session_id: str | None
    generated_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Agent service starting up")
    app.state.agent = AnalyticsAgent()
    yield


app = FastAPI(
    title="EnterpriseIQ Analytics Agent Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="ml-agent-service")


@app.post("/internal/agent/nl2sql", response_model=AgentQueryResponse)
async def nl_to_sql(req: AgentQueryRequest):
    try:
        agent: AnalyticsAgent = app.state.agent
        result: AgentResult = agent.query(
            question=req.question,
            dataset_id=req.dataset_id,
            session_id=req.session_id,
        )

        return AgentQueryResponse(
            question=result.question,
            sql_generated=result.sql_generated,
            results=result.results,
            chart_suggestion=result.chart_suggestion,
            explanation=result.explanation,
            row_count=result.row_count,
            dataset_id=result.dataset_id,
            query_id=result.query_id,
            session_id=result.session_id,
            generated_at=result.generated_at,
        )
    except Exception as e:
        logger.error("Agent query failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
