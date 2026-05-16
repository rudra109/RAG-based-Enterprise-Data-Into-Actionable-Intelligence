"""
EnterpriseIQ Backend — Main FastAPI Application
Developer A — REST API Layer
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings
from app.core.logging_setup import setup_logging
from app.routers import agent, anomaly, auth, forecast, kg, notifications, pipeline, rag

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Application Lifecycle ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    logger.info(
        "EnterpriseIQ Backend starting",
        environment=settings.environment,
        version="1.0.0",
    )
    yield
    logger.info("EnterpriseIQ Backend shutting down")


# ── App Factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="EnterpriseIQ API",
        description="""
## EnterpriseIQ — Data & Intelligence Platform API

The unified REST API layer for the EnterpriseIQ platform, built by **Developer A**.

### Modules
- **RAG** `/v1/rag/*` — Document ingestion and semantic Q&A
- **Pipeline** `/v1/pipeline/*` — Data ingestion and validation pipelines
- **Analytics Agent** `/v1/agent/*` — Natural language to SQL queries
- **Anomaly Detection** `/v1/anomaly/*` — ML-powered outlier detection
- **Forecasting** `/v1/forecast/*` — Time-series prediction
- **Knowledge Graph** `/v1/kg/*` — Entity and relationship extraction
- **Auth** `/v1/auth/*` — Firebase Auth, user & workspace management
- **Notifications** `/v1/notifications/*` + WebSocket `/ws/events`
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ───────────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Request Timing Middleware ────────────────────────────────────────────

    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        t0 = time.perf_counter()
        response: Response = await call_next(request)
        elapsed = (time.perf_counter() - t0) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.2f}"
        return response

    # ── Rate Limiting (simple Redis-based) ───────────────────────────────────

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if request.url.path.startswith(("/docs", "/redoc", "/openapi", "/health", "/metrics")):
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        try:
            from app.core.clients import get_cache
            cache = get_cache()
            key = f"rate:{client_ip}"
            count = cache.increment(key, ttl=60)
            if count > settings.rate_limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again in 60 seconds."},
                )
        except Exception:
            pass  # Don't block if Redis unavailable
        return await call_next(request)

    # ── Prometheus Metrics ────────────────────────────────────────────────────

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # ── Routers ──────────────────────────────────────────────────────────────

    app.include_router(auth.router)
    app.include_router(rag.router)
    app.include_router(pipeline.router)
    app.include_router(agent.router)
    app.include_router(anomaly.router)
    app.include_router(forecast.router)
    app.include_router(kg.router)
    app.include_router(notifications.router)

    # ── Health & Root ─────────────────────────────────────────────────────────

    @app.get("/health", tags=["Health"], summary="Health check")
    async def health():
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.environment,
            "timestamp": time.time(),
        }

    @app.get("/", tags=["Health"], summary="API root")
    async def root():
        return {
            "name": "EnterpriseIQ API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    # ── Global Exception Handler ──────────────────────────────────────────────

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", path=str(request.url), error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
    )
