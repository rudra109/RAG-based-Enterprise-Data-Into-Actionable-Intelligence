# EnterpriseIQ Backend — Developer A

## Overview

FastAPI-based REST API layer that sits between the frontend (Developer C) and the ML services (Developer B).

## Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   ├── auth.py              # Firebase Auth middleware
│   │   ├── clients.py           # BigQuery, GCS, Firestore, PubSub, Redis
│   │   ├── ml_client.py         # HTTP proxy to Developer B's ML services
│   │   └── logging_setup.py     # Structured JSON logging
│   ├── routers/
│   │   ├── auth.py              # /v1/auth/*
│   │   ├── rag.py               # /v1/rag/*
│   │   ├── pipeline.py          # /v1/pipeline/*
│   │   ├── agent.py             # /v1/agent/*
│   │   ├── anomaly.py           # /v1/anomaly/*
│   │   ├── forecast.py          # /v1/forecast/*
│   │   ├── kg.py                # /v1/kg/*
│   │   └── notifications.py     # /v1/notifications/* + /ws/events
│   └── services/
│       └── pipeline_service.py  # Document ingestion, data validation pipelines
├── tests/
│   ├── conftest.py              # Fixtures (mocked GCP + Firebase)
│   ├── test_rag.py
│   ├── test_pipeline.py
│   ├── test_api.py              # Agent, anomaly, forecast, KG
│   └── test_auth.py
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## API Endpoints

| Module | Endpoints |
|--------|-----------|
| **Auth** | `GET/PUT /v1/auth/profile`, `GET/POST /v1/auth/workspaces`, `POST /v1/auth/workspaces/{id}/invite` |
| **RAG** | `POST /v1/rag/ingest`, `POST /v1/rag/query`, `GET /v1/rag/documents`, `POST/GET/DELETE /v1/rag/corpus` |
| **Pipeline** | `POST/GET /v1/pipeline`, `GET /v1/pipeline/{id}/status`, `POST /v1/pipeline/{id}/trigger`, `GET /v1/pipeline/{id}/runs` |
| **Agent** | `POST /v1/agent/query`, `POST/GET/DELETE /v1/agent/datasets` |
| **Anomaly** | `POST /v1/anomaly/detect`, `GET /v1/anomaly/list`, `POST /v1/anomaly/acknowledge`, `GET /v1/anomaly/summary` |
| **Forecast** | `POST /v1/forecast/run`, `GET /v1/forecast/results`, `GET /v1/forecast/history` |
| **KG** | `POST/GET /v1/kg/graphs`, `POST /v1/kg/extract`, `POST /v1/kg/query`, `GET /v1/kg/subgraph` |
| **Notifications** | `GET /v1/notifications`, `POST /v1/notifications/{id}/read`, `GET/PUT /v1/notifications/preferences` |
| **WebSocket** | `WS /ws/events` — real-time anomaly alerts |

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and fill in environment variables
cp .env.example .env

# 3. Run development server
uvicorn app.main:app --reload --port 8080

# 4. Visit API docs
open http://localhost:8080/docs
```

## Running Tests

```bash
pytest -v
```

## Running Full Stack (Dev A + Dev B)

From the project root:
```bash
docker-compose up
```

Services:
- Backend API: http://localhost:8080/docs
- RAG Service: http://localhost:8001/docs
- Anomaly Service: http://localhost:8002/docs
- Forecast Service: http://localhost:8003/docs
- Agent Service: http://localhost:8004/docs
- KG Service: http://localhost:8005/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Integration with Developer B

Developer A calls Developer B's services via HTTP. The `ml_client.py` handles:
- Schema normalization between A's domain model and B's internal schemas
- Retry logic and error propagation
- Timeout management (120s default)

All ML results are:
1. Proxied from Developer B's services
2. Persisted to BigQuery by Developer A
3. Cached in Redis by Developer A
4. Returned to Developer C's frontend
