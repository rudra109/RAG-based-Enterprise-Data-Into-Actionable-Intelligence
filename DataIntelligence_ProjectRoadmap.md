# 🧠 EnterpriseIQ — Data & Intelligence Platform
### Full-Stack AI-Powered Enterprise Intelligence System
### 1-Year Project Roadmap | 3-Person Team | Google/Gemini-First Architecture

---

> **Vision:** Transform raw enterprise data into actionable intelligence using a fully integrated platform powered by Google Cloud, Gemini AI, and Vertex AI — delivering RAG systems, AI pipelines, natural language analytics, anomaly detection, forecasting, and knowledge graph extraction in one unified product.

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Team Roles & Responsibilities](#4-team-roles--responsibilities)
5. [Shared Contracts (Month 0 — Pre-Work)](#5-shared-contracts-month-0--pre-work)
6. [Person A — Backend & Data Engineer Roadmap](#6-person-a--backend--data-engineer-roadmap)
7. [Person B — ML & AI Engineer Roadmap](#7-person-b--ml--ai-engineer-roadmap)
8. [Person C — Frontend & UX Engineer Roadmap](#8-person-c--frontend--ux-engineer-roadmap)
9. [Combined Monthly Timeline](#9-combined-monthly-timeline)
10. [Infrastructure & DevOps](#10-infrastructure--devops)
11. [Testing Strategy](#11-testing-strategy)
12. [Milestone Deliverables](#12-milestone-deliverables)
13. [Success Metrics & KPIs](#13-success-metrics--kpis)

---

## 1. Project Overview

### Problem Statement
Enterprises sit on mountains of proprietary data — documents, databases, logs, spreadsheets — but lack the intelligence layer to query, understand, monitor, and act on it in real time.

### Solution: EnterpriseIQ
A **unified data intelligence platform** with five core capabilities:

| Module | Description | Primary Google/Gemini Tech |
|--------|-------------|---------------------------|
| **RAG Engine** | Multi-source document Q&A over proprietary data | Vertex AI Search + Gemini 1.5 Pro + Vector Search |
| **AI Data Pipeline** | Intelligent ingestion, validation, and enrichment | Cloud Dataflow + Gemini Flash + BigQuery |
| **Analytics Agent** | Natural language querying over structured data | Gemini Function Calling + BigQuery + Looker Studio |
| **Anomaly & Forecast** | Detect outliers and predict future trends | Vertex AI + AutoML Forecasting + Cloud Monitoring |
| **Knowledge Graph** | Extract entities and relationships from documents | Gemini Pro + Cloud Natural Language + Spanner Graph |

### Core Principles
- **Independence First:** All three engineers work on separate, non-blocking layers with pre-agreed API contracts and mock servers
- **Google-Native:** Prefer Google Cloud and Gemini services over third-party equivalents
- **Production-Grade:** Security, observability, CI/CD, and scale built in from month one
- **Incremental Delivery:** Working software every 4 weeks, not big-bang releases

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PERSON C — FRONTEND LAYER                        │
│                                                                         │
│  Next.js 14 App (App Router)  ·  Tailwind CSS  ·  Firebase Hosting     │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  RAG Chat UI │  │  NL Query UI │  │ Anomaly Dash │  │ KG Viewer │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘  │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │               Analytics Dashboard · Recharts · D3.js               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / WebSocket
┌───────────────────────────────────▼─────────────────────────────────────┐
│                       PERSON A — BACKEND & API LAYER                    │
│                                                                         │
│  FastAPI (Python 3.12)  ·  Cloud Run  ·  Firebase Auth  ·  Redis Cache │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ RAG API  │  │Pipeline  │  │Analytics │  │Anomaly   │  │KG API   │ │
│  │/v1/rag   │  │  API     │  │  API     │  │  API     │  │/v1/kg   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │              │              │              │              │      │
│  ┌────▼──────────────▼──────────────▼──────────────▼──────────── ▼──┐  │
│  │           Data Access Layer · BigQuery Client · GCS Client        │  │
│  └────────────────────────────────────────────────────────────────── ┘  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                     PERSON B — ML & INTELLIGENCE LAYER                  │
│                                                                         │
│  Vertex AI  ·  Gemini API  ·  Cloud Natural Language  ·  AutoML        │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  RAG Engine  │  │  Anomaly     │  │  Forecasting │  │    KG     │  │
│  │  (Gemini +   │  │  Detection   │  │  (Vertex AI  │  │Extraction │  │
│  │ Vector Search│  │  (Isolation  │  │   AutoML)    │  │(Gemini +  │  │
│  │     )        │  │   Forest)    │  │              │  │  NLP API) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                          SHARED DATA LAYER                              │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │   BigQuery  │  │  Cloud GCS  │  │  Firestore │  │ Vertex Vector │  │
│  │  Data Wrhse │  │  Raw Store  │  │  (Metadata)│  │    Search     │  │
│  └─────────────┘  └─────────────┘  └────────────┘  └───────────────┘  │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐                      │
│  │  Cloud      │  │  Pub/Sub    │  │  Spanner   │                      │
│  │  Dataflow   │  │  (Events)   │  │   Graph    │                      │
│  └─────────────┘  └─────────────┘  └────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Independence Architecture
```
SHARED LAYER (defined Week 1):
  ├── /contracts/openapi.yaml       → All REST API specs
  ├── /contracts/event-schemas/     → Pub/Sub message schemas
  ├── /contracts/bigquery-schemas/  → All BQ table schemas
  └── /contracts/mock-server/       → Mock API server (Person C uses this)

Person A works against: Real BigQuery + GCS + Firestore
Person B works against: Vertex AI + Gemini API + Real data schemas
Person C works against: Mock server → switches to real APIs in Month 4
```

---

## 3. Technology Stack

### 🌐 Google / Gemini Technologies (Primary)

| Category | Technology | Usage |
|----------|-----------|-------|
| **LLM / AI** | Gemini 1.5 Pro | RAG Q&A, knowledge extraction, complex reasoning |
| **LLM / AI** | Gemini 1.5 Flash | Fast validation, classification, NL-to-SQL |
| **LLM / AI** | Gemini Embedding (text-embedding-004) | Document embeddings for RAG |
| **ML Platform** | Vertex AI | Model training, deployment, MLOps |
| **ML - Forecasting** | Vertex AI AutoML Forecasting | Time-series prediction |
| **Search / RAG** | Vertex AI Search (Discovery Engine) | Enterprise search & RAG grounding |
| **Vector DB** | Vertex AI Vector Search (Matching Engine) | Semantic similarity search |
| **Data Warehouse** | BigQuery | Structured data storage and analytics |
| **Data Pipeline** | Cloud Dataflow (Apache Beam) | Batch & streaming data pipelines |
| **Messaging** | Cloud Pub/Sub | Event-driven architecture |
| **Object Storage** | Google Cloud Storage (GCS) | Raw file/document store |
| **Database** | Cloud Firestore | Metadata, config, user data |
| **Graph Database** | Cloud Spanner Graph | Knowledge graph storage |
| **NLP** | Cloud Natural Language API | Entity extraction, sentiment |
| **Auth** | Firebase Authentication | User auth (Google SSO, email) |
| **Hosting** | Firebase Hosting | Frontend static hosting |
| **Compute** | Cloud Run | Containerized backend services |
| **Orchestration** | Cloud Composer (Airflow) | ML pipeline orchestration |
| **Monitoring** | Cloud Monitoring + Cloud Logging | Observability |
| **CI/CD** | Cloud Build + Artifact Registry | Automated build & deploy |
| **CDN / Cache** | Cloud CDN + Memorystore (Redis) | Caching layer |
| **API Gateway** | Cloud Endpoints / API Gateway | Rate limiting, auth enforcement |
| **Analytics UI** | Looker Studio (embedded) | Advanced analytics dashboards |
| **Secret Mgmt** | Secret Manager | API keys and credentials |

### 🔧 Supporting Technologies

| Category | Technology |
|----------|-----------|
| Backend Framework | FastAPI (Python 3.12) |
| Frontend Framework | Next.js 14 (App Router) |
| UI Components | Tailwind CSS + shadcn/ui |
| Data Visualization | Recharts + D3.js + Cytoscape.js (graphs) |
| ML Libraries | scikit-learn, Prophet, LightGBM, LangChain-Google |
| Containerization | Docker + Cloud Run |
| IaC | Terraform (Google Cloud provider) |
| Testing | Pytest (backend), Jest/Playwright (frontend), Locust (load) |
| Version Control | GitHub + GitHub Actions |

---

## 4. Team Roles & Responsibilities

### 👤 Person A — Backend & Data Engineer
**Focus:** Data infrastructure, REST APIs, authentication, data pipelines, storage schemas

**Owns:**
- FastAPI backend application (all `/v1/*` endpoints)
- Cloud Dataflow ingestion pipelines
- BigQuery schema design and optimization
- GCS bucket architecture and lifecycle policies
- Firestore collections for metadata
- Firebase Auth integration and JWT middleware
- Cloud Run deployment configs
- API Gateway setup and rate limiting
- Redis caching layer
- Integration with ML services (calling Person B's deployed models)

**Does NOT own:**
- ML model training or Vertex AI model configs (Person B)
- Frontend components or UI (Person C)
- Gemini prompt engineering (Person B)

---

### 👤 Person B — ML & AI Engineer
**Focus:** All AI/ML components — RAG, anomaly detection, forecasting, knowledge graph, agents

**Owns:**
- Gemini API integration and prompt engineering
- Vertex AI Vector Search index management
- RAG pipeline (chunking, embedding, retrieval, generation)
- Anomaly detection model (Isolation Forest + Vertex AI)
- Time-series forecasting (Vertex AI AutoML + Prophet)
- Knowledge graph extraction pipeline (Gemini + Cloud NLP)
- Analytics agent (Gemini function calling + NL-to-BigQuery-SQL)
- Vertex AI model deployment and versioning
- Cloud Composer DAGs for ML pipeline orchestration
- Model evaluation, monitoring, drift detection
- Spanner Graph schema and queries

**Does NOT own:**
- REST API layer (Person A exposes ML results via REST)
- Frontend rendering (Person C)
- Data ingestion from source systems (Person A's pipelines feed Person B's models)

---

### 👤 Person C — Frontend & UX Engineer
**Focus:** All user-facing interfaces, dashboards, visualizations, UX flows

**Owns:**
- Next.js 14 application structure
- RAG Chat Interface (document Q&A UI)
- Natural Language Query UI (analytics agent frontend)
- Anomaly Detection Dashboard
- Forecasting Charts (time-series visualization)
- Knowledge Graph Visualizer (interactive graph explorer)
- Pipeline Monitor (data pipeline status UI)
- User Authentication flows (Firebase Auth frontend)
- Firebase Hosting deployment
- Looker Studio embedded reports
- Responsive design and accessibility
- API integration layer (connects to Person A's endpoints)

**Does NOT own:**
- Backend REST API logic (Person A)
- ML models or AI logic (Person B)
- BigQuery queries or data schemas (Person A)

---

### 🤝 Collaboration Points (Minimal, Pre-defined)

| When | Who | What |
|------|-----|------|
| Week 1 | A + B + C | Define all API contracts, schemas, event formats |
| Month 2 end | A + C | Person C switches from mock to real staging APIs |
| Month 4 end | A + B | Person A integrates Person B's first deployed models |
| Month 6 | All 3 | Integration sprint — connect all three layers |
| Month 9 | All 3 | Performance + UX review |
| Month 12 | All 3 | Final release, documentation, handoff |

---

## 5. Shared Contracts (Month 0 — Pre-Work)

> **This section is completed in Week 1 by all three engineers together. Once agreed, no changes without team vote. This is what enables 100% parallel work.**

### 5.1 API Contract Summary (OpenAPI 3.1)

```yaml
# /contracts/openapi.yaml (abbreviated)

paths:

  # RAG ENDPOINTS
  /v1/rag/ingest:
    post:
      summary: Ingest a document into the RAG corpus
      requestBody:
        content:
          multipart/form-data:
            schema:
              properties:
                file: { type: string, format: binary }
                corpus_id: { type: string }
                metadata: { type: object }

  /v1/rag/query:
    post:
      summary: Query the RAG system
      requestBody:
        content:
          application/json:
            schema:
              properties:
                question: { type: string }
                corpus_id: { type: string }
                top_k: { type: integer, default: 5 }
      responses:
        '200':
          content:
            application/json:
              schema:
                properties:
                  answer: { type: string }
                  sources: { type: array, items: { $ref: '#/components/schemas/Source' } }
                  confidence: { type: number }

  # ANALYTICS AGENT ENDPOINTS
  /v1/agent/query:
    post:
      summary: Natural language query over structured data
      requestBody:
        content:
          application/json:
            schema:
              properties:
                question: { type: string }
                dataset_id: { type: string }
      responses:
        '200':
          content:
            application/json:
              schema:
                properties:
                  sql_generated: { type: string }
                  results: { type: array }
                  chart_suggestion: { type: string, enum: [bar, line, pie, table, scatter] }
                  explanation: { type: string }

  # ANOMALY ENDPOINTS
  /v1/anomaly/detect:
    post:
      summary: Run anomaly detection on a dataset
      requestBody:
        content:
          application/json:
            schema:
              properties:
                dataset_id: { type: string }
                time_column: { type: string }
                metric_columns: { type: array, items: { type: string } }
                sensitivity: { type: string, enum: [low, medium, high], default: medium }

  /v1/anomaly/list:
    get:
      summary: List detected anomalies
      parameters:
        - name: dataset_id
          in: query
        - name: start_time
          in: query
          schema: { type: string, format: date-time }

  # FORECASTING ENDPOINTS
  /v1/forecast/run:
    post:
      summary: Generate a forecast
      requestBody:
        content:
          application/json:
            schema:
              properties:
                dataset_id: { type: string }
                target_column: { type: string }
                horizon_days: { type: integer }
                confidence_level: { type: number, default: 0.95 }

  /v1/forecast/results:
    get:
      summary: Get forecast results
      parameters:
        - name: forecast_id
          in: query

  # KNOWLEDGE GRAPH ENDPOINTS
  /v1/kg/extract:
    post:
      summary: Extract knowledge graph from documents
      requestBody:
        content:
          application/json:
            schema:
              properties:
                document_ids: { type: array, items: { type: string } }
                graph_id: { type: string }

  /v1/kg/query:
    post:
      summary: Query the knowledge graph
      requestBody:
        content:
          application/json:
            schema:
              properties:
                graph_id: { type: string }
                query: { type: string }
                query_type: { type: string, enum: [natural_language, gql] }

  /v1/kg/subgraph:
    get:
      summary: Get a subgraph centered on an entity
      parameters:
        - name: entity_id
          in: query
        - name: depth
          in: query
          schema: { type: integer, default: 2 }

  # PIPELINE ENDPOINTS
  /v1/pipeline/create:
    post:
      summary: Create a new data pipeline

  /v1/pipeline/{pipeline_id}/status:
    get:
      summary: Get pipeline status and stats

  /v1/pipeline/{pipeline_id}/trigger:
    post:
      summary: Manually trigger a pipeline run
```

### 5.2 BigQuery Schema Contracts

```sql
-- DATASET: enterpriseiq_core

-- Documents table
CREATE TABLE documents (
  doc_id STRING NOT NULL,
  filename STRING,
  gcs_uri STRING,
  corpus_id STRING,
  upload_timestamp TIMESTAMP,
  file_type STRING,
  size_bytes INT64,
  status STRING,   -- 'ingesting' | 'indexed' | 'failed'
  metadata JSON,
  embedding_count INT64
);

-- Chunks table (RAG)
CREATE TABLE doc_chunks (
  chunk_id STRING NOT NULL,
  doc_id STRING NOT NULL,
  corpus_id STRING,
  chunk_text STRING,
  chunk_index INT64,
  embedding_id STRING,   -- ID in Vector Search index
  page_number INT64,
  token_count INT64,
  created_at TIMESTAMP
);

-- Anomaly results
CREATE TABLE anomaly_results (
  anomaly_id STRING NOT NULL,
  dataset_id STRING,
  detected_at TIMESTAMP,
  metric_name STRING,
  anomaly_score FLOAT64,
  actual_value FLOAT64,
  expected_value FLOAT64,
  lower_bound FLOAT64,
  upper_bound FLOAT64,
  is_acknowledged BOOL,
  severity STRING   -- 'low' | 'medium' | 'high' | 'critical'
);

-- Forecast results
CREATE TABLE forecast_results (
  forecast_id STRING NOT NULL,
  dataset_id STRING,
  target_column STRING,
  forecast_timestamp TIMESTAMP,
  predicted_value FLOAT64,
  lower_bound FLOAT64,
  upper_bound FLOAT64,
  confidence_level FLOAT64,
  model_version STRING
);

-- Knowledge graph nodes
CREATE TABLE kg_nodes (
  node_id STRING NOT NULL,
  graph_id STRING,
  entity_type STRING,
  entity_name STRING,
  properties JSON,
  source_doc_id STRING,
  confidence FLOAT64,
  created_at TIMESTAMP
);

-- Knowledge graph edges
CREATE TABLE kg_edges (
  edge_id STRING NOT NULL,
  graph_id STRING,
  source_node_id STRING,
  target_node_id STRING,
  relationship_type STRING,
  properties JSON,
  source_doc_id STRING,
  confidence FLOAT64
);

-- Pipeline runs
CREATE TABLE pipeline_runs (
  run_id STRING NOT NULL,
  pipeline_id STRING,
  pipeline_name STRING,
  status STRING,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  records_processed INT64,
  records_failed INT64,
  error_message STRING
);
```

### 5.3 Pub/Sub Event Schema Contracts

```json
// Topic: enterpriseiq.document.ingested
{
  "event_type": "document.ingested",
  "doc_id": "string",
  "corpus_id": "string",
  "gcs_uri": "string",
  "file_type": "pdf|docx|csv|json|txt",
  "timestamp": "ISO8601",
  "triggered_by": "api|pipeline|scheduled"
}

// Topic: enterpriseiq.anomaly.detected
{
  "event_type": "anomaly.detected",
  "anomaly_id": "string",
  "dataset_id": "string",
  "severity": "low|medium|high|critical",
  "metric_name": "string",
  "anomaly_score": 0.95,
  "timestamp": "ISO8601"
}

// Topic: enterpriseiq.pipeline.completed
{
  "event_type": "pipeline.completed",
  "pipeline_id": "string",
  "run_id": "string",
  "status": "success|partial|failed",
  "records_processed": 10000,
  "duration_seconds": 45,
  "timestamp": "ISO8601"
}

// Topic: enterpriseiq.forecast.ready
{
  "event_type": "forecast.ready",
  "forecast_id": "string",
  "dataset_id": "string",
  "target_column": "string",
  "horizon_days": 30,
  "timestamp": "ISO8601"
}
```

---

## 6. Person A — Backend & Data Engineer Roadmap

### Overview
Person A builds the data foundation and API layer. All ML results from Person B are served through Person A's APIs. Person C consumes these APIs.

---

### 📅 Month 1 — Foundation & Contracts

**Week 1-2: Project Setup**
- [ ] Create GCP project `enterpriseiq-prod` and `enterpriseiq-dev`
- [ ] Set up Terraform workspace for all GCP resources
- [ ] Create all BigQuery datasets and tables (per Section 5.2 schemas)
- [ ] Set up GCS buckets: `raw-uploads`, `processed-docs`, `ml-artifacts`, `pipeline-temp`
- [ ] Enable all required GCP APIs (BigQuery, Dataflow, Pub/Sub, Vertex AI, etc.)
- [ ] Set up Service Accounts with least-privilege IAM
- [ ] Set up Secret Manager with all credential stubs
- [ ] Create GitHub repository structure:
  ```
  /backend/         ← Person A's workspace
  /ml/              ← Person B's workspace  
  /frontend/        ← Person C's workspace
  /contracts/       ← Shared (all 3)
  /infrastructure/  ← Terraform (Person A)
  ```

**Week 3-4: Mock Server + Auth**
- [ ] Build FastAPI skeleton with all routes returning mock data (from OpenAPI spec)
- [ ] Deploy mock server to Cloud Run (Person C can start immediately)
- [ ] Implement Firebase Auth middleware (JWT validation)
- [ ] Set up Cloud Endpoints / API Gateway with Firebase Auth
- [ ] Implement user management endpoints (`/v1/auth/profile`, `/v1/auth/workspaces`)
- [ ] Set up Firestore collections: `users`, `workspaces`, `corpora`, `pipelines`
- [ ] Write Terraform for all infrastructure

**Deliverable:** Fully deployed mock server + auth. Person C unblocked from Day 1.

---

### 📅 Month 2 — Data Ingestion Pipelines

**Core Pipelines (Cloud Dataflow / Apache Beam):**

**Pipeline 1: Document Ingestion Pipeline**
```python
# Beam pipeline: GCS trigger → extract text → chunk → emit event
class DocumentIngestionPipeline:
    steps:
      1. Read file from GCS (PDF/DOCX/TXT/CSV)
      2. Extract text (pdfminer, python-docx, pandas)
      3. Chunk text (512 tokens, 50 token overlap)
      4. Write chunks to BigQuery (doc_chunks table)
      5. Update document status in BigQuery (documents table)
      6. Publish to Pub/Sub: enterpriseiq.document.ingested
      7. Write metadata to Firestore
```

**Pipeline 2: Structured Data Validator Pipeline**
```python
# Beam pipeline: BigQuery source → validate → enrich → write
class DataValidatorPipeline:
    steps:
      1. Read records from BigQuery or GCS CSV
      2. Validate schema (pydantic models, type checks)
      3. Detect missing/null columns, outlier values
      4. Call Gemini Flash for semantic validation (optional)
      5. Write valid records to target BigQuery table
      6. Write invalid records to error table with reasons
      7. Emit pipeline completion event
```

**Pipeline 3: Multi-Source Connector Pipeline**
```python
# Connectors: REST API, SFTP, Google Sheets, Salesforce SFDC
class MultiSourceConnector:
    supported_sources:
      - REST API (OAuth2 / API Key)
      - Google Sheets (Sheets API v4)
      - GCS files (CSV, JSON, Parquet)
      - PostgreSQL / MySQL via Cloud SQL Proxy
      - BigQuery external tables
    output: Normalized records in BigQuery staging tables
```

- [ ] Build all three pipelines with Dataflow runner
- [ ] Implement Cloud Scheduler for scheduled pipeline runs
- [ ] Set up Dead Letter Queue (DLQ) for failed records
- [ ] Implement pipeline monitoring with Cloud Monitoring
- [ ] Build `/v1/pipeline/*` real endpoints (replacing mocks)

---

### 📅 Month 3 — Core RAG Backend API

**RAG API Implementation (calling Person B's Vector Search index):**

```python
# /v1/rag/ingest — Real implementation
async def ingest_document(file: UploadFile, corpus_id: str):
    # 1. Save to GCS raw bucket
    gcs_uri = await gcs_client.upload(file, f"raw-uploads/{corpus_id}/{uuid}")
    
    # 2. Trigger Document Ingestion Pipeline (Dataflow)
    job = dataflow_client.run_pipeline("doc-ingestion", {
        "gcs_uri": gcs_uri,
        "corpus_id": corpus_id,
        "doc_id": doc_id
    })
    
    # 3. Create document record in BigQuery
    await bq_client.insert("documents", {...})
    
    # 4. Return job status (chunking + embedding done by Person B's pipeline)
    return {"doc_id": doc_id, "status": "processing", "job_id": job.id}

# /v1/rag/query — Calls Person B's RAG service
async def query_rag(question: str, corpus_id: str, top_k: int):
    # Calls Person B's internal RAG service (HTTP call to ml-service)
    result = await ml_service_client.post("/internal/rag/query", {
        "question": question,
        "corpus_id": corpus_id,
        "top_k": top_k
    })
    return result
```

- [ ] Implement real `/v1/rag/ingest` with GCS + Dataflow
- [ ] Implement real `/v1/rag/query` proxying to Person B's ML service
- [ ] Implement corpus management (`/v1/rag/corpus/create`, `/list`, `/delete`)
- [ ] Add Redis caching for frequent queries (TTL: 1 hour)
- [ ] Implement document versioning and re-indexing
- [ ] Add rate limiting per workspace

---

### 📅 Month 4 — Analytics & Anomaly APIs

**Analytics Agent API:**
```python
# /v1/agent/query
async def agent_query(question: str, dataset_id: str):
    # 1. Get dataset schema from BigQuery
    schema = await bq_client.get_table_schema(dataset_id)
    
    # 2. Call Person B's NL-to-SQL service
    sql_result = await ml_service_client.post("/internal/agent/nl2sql", {
        "question": question,
        "schema": schema
    })
    
    # 3. Execute generated SQL in BigQuery (with safety checks)
    if validate_sql(sql_result["sql"]):  # whitelist only SELECT
        results = await bq_client.query(sql_result["sql"])
    
    # 4. Return results + chart suggestion + explanation
    return {
        "sql_generated": sql_result["sql"],
        "results": results.to_dict(),
        "chart_suggestion": sql_result["chart_type"],
        "explanation": sql_result["explanation"]
    }
```

- [ ] Implement `/v1/agent/*` endpoints
- [ ] Implement SQL safety validator (only SELECT, no DDL/DML)
- [ ] Build dataset registry (register BQ tables for NL querying)
- [ ] Implement `/v1/anomaly/*` endpoints proxying to Person B
- [ ] Implement `/v1/forecast/*` endpoints proxying to Person B
- [ ] Add BigQuery result caching (materialized query results)

---

### 📅 Month 5 — Knowledge Graph & Notifications

**Knowledge Graph API:**
- [ ] Implement `/v1/kg/extract` triggering Person B's extraction pipeline
- [ ] Implement `/v1/kg/query` with both GQL and NL modes
- [ ] Implement `/v1/kg/subgraph` for graph exploration
- [ ] Build Spanner Graph read layer for KG queries

**Real-time Notifications:**
- [ ] WebSocket endpoint (`/ws/events`) for real-time anomaly alerts
- [ ] Pub/Sub push subscription → Firebase Cloud Messaging
- [ ] Email notification service (SendGrid or Gmail API)
- [ ] Notification preferences per user in Firestore

**Security Hardening:**
- [ ] Implement workspace-level data isolation (row-level security in BigQuery)
- [ ] Add Cloud Armor WAF rules
- [ ] Implement audit logging (all API calls to BigQuery audit table)
- [ ] Set up VPC Service Controls for data perimeter

---

### 📅 Month 6 — Integration Sprint

- [ ] Integration testing with Person B's deployed ML services
- [ ] End-to-end API tests with Person C's frontend
- [ ] Performance testing (Locust): 1000 concurrent users
- [ ] BigQuery query optimization (partitioning, clustering)
- [ ] Redis cache hit rate optimization
- [ ] Cloud Run autoscaling tuning (min 2, max 20 instances)
- [ ] API documentation (Swagger UI, Redoc) deployed to Cloud Run

---

### 📅 Months 7–9 — Optimization & Scale

- [ ] Implement streaming analytics with BigQuery Storage Write API
- [ ] Build data lineage tracking (every record traceable to source)
- [ ] Implement multi-region failover for Cloud Run
- [ ] Add GraphQL endpoint (alternative to REST) using Strawberry
- [ ] Build export API (CSV, JSON, Parquet export from any BQ table)
- [ ] Implement API versioning strategy (v1 → v2 without breaking changes)
- [ ] Add RBAC (roles: admin, analyst, viewer, pipeline-editor)
- [ ] BigQuery column-level security for PII fields

---

### 📅 Months 10–12 — Enterprise Features & Polish

- [ ] Google Workspace integration (Drive ingestion, Gmail trigger)
- [ ] Webhook support (outbound webhooks on anomaly / pipeline events)
- [ ] API usage analytics dashboard (Cloud Monitoring + Looker Studio)
- [ ] Tenant onboarding automation (new workspace in < 5 min)
- [ ] SLA monitoring and alerting (Cloud Monitoring uptime checks)
- [ ] Complete API documentation and developer portal
- [ ] Load testing at 10x projected scale
- [ ] Final security audit and penetration testing

---

## 7. Person B — ML & AI Engineer Roadmap

### Overview
Person B builds all intelligence — Gemini-powered RAG, ML models, knowledge graph extraction, and the analytics agent. Person B deploys internal ML services that Person A's backend calls.

---

### 📅 Month 1 — Foundation & Research

**Week 1-2: Environment Setup**
- [ ] Set up Vertex AI Workbench notebooks for experimentation
- [ ] Configure Gemini API access (Gemini 1.5 Pro + Flash)
- [ ] Set up Vertex AI Vector Search index (stream update mode)
  ```python
  # Vector Search index config
  index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
      display_name="enterpriseiq-rag-index",
      dimensions=768,  # text-embedding-004 dimensions
      approximate_neighbors_count=10,
      distance_measure_type="DOT_PRODUCT_DISTANCE",
  )
  ```
- [ ] Set up Cloud Composer (Airflow) environment for ML pipeline DAGs
- [ ] Create Vertex AI Pipeline templates
- [ ] Set up ML experiment tracking (Vertex AI Experiments)
- [ ] Benchmark Gemini 1.5 Pro vs Flash for each use case

**Week 3-4: RAG Research & Prototyping**
- [ ] Test chunking strategies (fixed-size, semantic, recursive)
- [ ] Benchmark `text-embedding-004` vs `textembedding-gecko` models
- [ ] Test Vertex AI Search vs custom Vector Search for RAG quality
- [ ] Prototype Gemini 1.5 Pro RAG chain with LangChain-Google
- [ ] Define evaluation metrics (RAGAS: faithfulness, relevancy, context recall)

---

### 📅 Month 2 — RAG Engine Implementation

**RAG Architecture:**
```python
# Full RAG Pipeline
class EnterpriseRAGEngine:
    
    # Step 1: Embedding Service
    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """Uses text-embedding-004 via Vertex AI"""
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = model.get_embeddings(chunks)
        return [e.values for e in embeddings]
    
    # Step 2: Index chunks into Vector Search
    def index_chunks(self, chunk_ids: list, embeddings: list):
        """Upserts into Vertex AI Vector Search index"""
        self.index_endpoint.upsert_datapoints([
            {"datapoint_id": cid, "feature_vector": emb}
            for cid, emb in zip(chunk_ids, embeddings)
        ])
    
    # Step 3: Retrieve relevant chunks
    def retrieve(self, question: str, corpus_id: str, top_k: int):
        """Semantic search in Vector Search"""
        query_embedding = self.embed_chunks([question])[0]
        neighbors = self.index_endpoint.find_neighbors(
            deployed_index_id=f"corpus_{corpus_id}",
            queries=[query_embedding],
            num_neighbors=top_k
        )
        # Fetch chunk text from BigQuery by chunk_id
        chunk_texts = self.bq_client.get_chunks(
            [n.datapoint.datapoint_id for n in neighbors[0]]
        )
        return chunk_texts
    
    # Step 4: Generate answer with Gemini
    def generate(self, question: str, chunks: list[ChunkResult]) -> RAGResponse:
        """Grounded generation using Gemini 1.5 Pro"""
        context = "\n\n".join([f"[{i+1}] {c.text}" for i, c in enumerate(chunks)])
        
        prompt = f"""You are an enterprise intelligence assistant.
Answer the question using ONLY the provided context.
If the answer is not in the context, say "I don't have enough information."
Always cite which source number ([1], [2], etc.) supports each claim.

Context:
{context}

Question: {question}

Answer:"""
        
        response = self.gemini_pro.generate_content(prompt)
        return RAGResponse(
            answer=response.text,
            sources=self._extract_citations(chunks),
            confidence=self._calculate_confidence(response)
        )
    
    # Step 5: Hybrid search (vector + keyword)
    def hybrid_search(self, question: str, corpus_id: str):
        """Combine Vector Search + BigQuery text search (BM25-like)"""
        vector_results = self.retrieve(question, corpus_id, top_k=10)
        keyword_results = self.bq_client.full_text_search(question, corpus_id)
        return self._reciprocal_rank_fusion(vector_results, keyword_results)
```

**Advanced RAG Features:**
- [ ] Multi-document RAG (query across multiple corpora simultaneously)
- [ ] Conversational RAG (maintain conversation history per session)
- [ ] RAG with Gemini grounding (ground on GCS or Google Search)
- [ ] Streaming responses (Server-Sent Events via FastAPI)
- [ ] RAG evaluation pipeline (RAGAS metrics logged to BigQuery)
- [ ] Re-ranking with Gemini (re-rank retrieved chunks before generation)

**Deploy Internal Service:**
- [ ] Deploy RAG service to Cloud Run as `ml-rag-service`
- [ ] Expose `/internal/rag/query` and `/internal/rag/embed` endpoints
- [ ] Only accessible from Person A's backend (VPC internal)

---

### 📅 Month 3 — Anomaly Detection System

**Anomaly Detection Architecture:**
```python
class AnomalyDetectionSystem:
    
    # Model 1: Statistical (fast, real-time)
    def statistical_detection(self, series: pd.Series) -> list[Anomaly]:
        """Z-score + IQR method for quick detection"""
        z_scores = np.abs(stats.zscore(series))
        iqr = series.quantile(0.75) - series.quantile(0.25)
        lower = series.quantile(0.25) - 1.5 * iqr
        upper = series.quantile(0.75) + 1.5 * iqr
        return [Anomaly(i, v, "statistical") 
                for i, v in enumerate(series) 
                if z_scores[i] > 3 or v < lower or v > upper]
    
    # Model 2: Isolation Forest (Vertex AI deployed)
    def isolation_forest_detection(self, df: pd.DataFrame) -> list[Anomaly]:
        """Multivariate anomaly detection via Vertex AI endpoint"""
        predictions = self.vertex_endpoint.predict(instances=df.to_dict('records'))
        return [Anomaly(i, score=-p, "isolation_forest")
                for i, p in enumerate(predictions.predictions)
                if -p > self.threshold]
    
    # Model 3: Gemini-powered semantic anomaly
    def semantic_anomaly_detection(self, records: list[dict]) -> list[Anomaly]:
        """Use Gemini to detect anomalies that are semantically unusual"""
        prompt = f"""Analyze these data records and identify any that seem 
        anomalous, suspicious, or inconsistent with the others.
        Explain why each anomaly is unusual.
        
        Records: {json.dumps(records[:50])}
        
        Return JSON: [{{"index": 0, "reason": "...", "severity": "low|medium|high"}}]"""
        
        response = self.gemini_flash.generate_content(prompt)
        return self._parse_anomaly_json(response.text)
    
    # Combined ensemble
    def detect(self, dataset_id: str, config: AnomalyConfig) -> AnomalyReport:
        data = self.bq_client.load_dataset(dataset_id)
        
        results = []
        if config.use_statistical: results += self.statistical_detection(data)
        if config.use_ml: results += self.isolation_forest_detection(data)
        if config.use_semantic: results += self.semantic_anomaly_detection(data)
        
        # Deduplicate and score
        return self._ensemble_vote(results)
```

**Vertex AI Model Training:**
- [ ] Prepare training dataset from BigQuery (historical data with labels)
- [ ] Train Isolation Forest on Vertex AI Custom Training
- [ ] Train LSTM autoencoder for time-series anomalies
- [ ] Deploy models to Vertex AI Endpoints
- [ ] Set up model monitoring (data drift detection)
- [ ] Implement streaming anomaly detection via Pub/Sub → Cloud Function

**Alerting Integration:**
- [ ] Publish anomaly events to `enterpriseiq.anomaly.detected` Pub/Sub topic
- [ ] Integrate with Cloud Monitoring for custom anomaly metrics
- [ ] Build anomaly severity scoring (rule-based + Gemini reasoning)

---

### 📅 Month 4 — Forecasting System

**Forecasting Architecture:**
```python
class ForecastingSystem:
    
    # Model 1: Vertex AI AutoML Forecasting
    def vertex_automl_forecast(self, dataset_id: str, 
                                target_col: str, horizon: int) -> ForecastResult:
        """Train and deploy AutoML time-series model"""
        # Create AutoML dataset from BigQuery
        dataset = aiplatform.TimeSeriesDataset.create(
            display_name=f"forecast_{dataset_id}",
            bq_source=f"bq://project.dataset.{dataset_id}"
        )
        
        # Train model
        job = aiplatform.AutoMLForecastingTrainingJob(
            display_name=f"forecast_{dataset_id}_{target_col}",
            optimization_objective="minimize-rmse",
            column_specs={target_col: "numeric", "timestamp": "timestamp"},
        )
        model = job.run(
            dataset=dataset,
            target_column=target_col,
            time_column="timestamp",
            forecast_horizon=horizon,
            context_window=horizon * 3,
        )
        return model
    
    # Model 2: Prophet (fast, interpretable)
    def prophet_forecast(self, series: pd.DataFrame, horizon: int) -> ForecastResult:
        """Facebook Prophet for interpretable forecasting"""
        from prophet import Prophet
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        model.fit(series.rename(columns={"timestamp": "ds", target_col: "y"}))
        future = model.make_future_dataframe(periods=horizon)
        forecast = model.predict(future)
        return ForecastResult(
            forecast=forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
            components=model.plot_components(forecast),
            changepoints=model.changepoints
        )
    
    # Gemini forecast explanation
    def explain_forecast(self, forecast: ForecastResult) -> str:
        """Use Gemini to explain forecast in plain English"""
        prompt = f"""Explain this forecast to a business user in plain English.
        Mention key trends, seasonality patterns, and any significant changes.
        Keep it under 100 words.
        
        Forecast summary: {forecast.summary_stats()}"""
        
        return self.gemini_flash.generate_content(prompt).text
```

- [ ] Implement Vertex AI AutoML Forecasting pipeline end-to-end
- [ ] Implement Prophet fallback model (for small datasets)
- [ ] Build forecast evaluation (MAE, RMSE, MAPE) logged to BigQuery
- [ ] Implement automated retraining trigger (when model drift detected)
- [ ] Deploy forecasting service to Cloud Run as `ml-forecast-service`
- [ ] Add confidence interval calculation and visualization data

---

### 📅 Month 5 — Analytics Agent (NL-to-SQL)

**Analytics Agent Architecture:**
```python
class AnalyticsAgent:
    
    def __init__(self):
        self.gemini = GenerativeModel("gemini-1.5-pro")
        self.tools = [
            FunctionDeclaration(
                name="execute_bigquery_query",
                description="Execute a SQL query on BigQuery and return results",
                parameters={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "The SQL query to execute"},
                        "limit": {"type": "integer", "description": "Max rows to return"}
                    }
                }
            ),
            FunctionDeclaration(
                name="get_table_schema",
                description="Get the schema of a BigQuery table",
                parameters={
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string"}
                    }
                }
            ),
            FunctionDeclaration(
                name="list_available_tables",
                description="List all tables available for querying",
                parameters={}
            )
        ]
        self.tool_config = Tool(function_declarations=self.tools)
    
    def query(self, question: str, dataset_id: str) -> AgentResult:
        """Multi-turn agent that generates and executes SQL"""
        schema = self.bq.get_dataset_schema(dataset_id)
        
        system_prompt = f"""You are an expert data analyst.
You have access to a BigQuery dataset with the following tables:
{schema}

When the user asks a question:
1. Generate a SQL query to answer it
2. Execute it using execute_bigquery_query
3. Interpret the results
4. Suggest the best chart type for visualization
5. Always use SELECT only (never INSERT/UPDATE/DELETE)"""
        
        chat = self.gemini.start_chat()
        
        # Agentic loop (max 5 turns)
        for turn in range(5):
            response = chat.send_message(
                question if turn == 0 else "[continue]",
                tools=self.tool_config
            )
            
            if response.candidates[0].finish_reason == "STOP":
                break
                
            # Handle function calls
            for part in response.parts:
                if hasattr(part, 'function_call'):
                    result = self._execute_function(part.function_call)
                    chat.send_message(
                        Part.from_function_response(
                            name=part.function_call.name,
                            response={"result": result}
                        )
                    )
        
        return self._parse_final_response(chat.history)
```

- [ ] Implement full Gemini Function Calling agent
- [ ] Build NL-to-SQL with schema-aware prompting
- [ ] Implement SQL safety sandbox (only SELECT, parameterized queries)
- [ ] Add chart type recommendation logic
- [ ] Support follow-up questions (multi-turn conversation)
- [ ] Build query explanation in plain English
- [ ] Deploy as `ml-agent-service` on Cloud Run

---

### 📅 Month 6 — Knowledge Graph Extraction

**Knowledge Graph Architecture:**
```python
class KnowledgeGraphExtractor:
    
    def extract_from_document(self, doc_text: str, doc_id: str) -> KGExtraction:
        
        # Step 1: Cloud Natural Language API for basic entities
        nl_client = language_v2.LanguageServiceClient()
        document = language_v2.Document(
            content=doc_text,
            type_=language_v2.Document.Type.PLAIN_TEXT
        )
        nl_entities = nl_client.analyze_entities(
            request={"document": document}
        ).entities
        
        # Step 2: Gemini Pro for rich relationship extraction
        prompt = f"""Extract all entities and relationships from this text.
        
        Return ONLY valid JSON in this format:
        {{
          "nodes": [
            {{"id": "unique_id", "type": "PERSON|ORG|PRODUCT|CONCEPT|LOCATION|EVENT", 
              "name": "entity name", "properties": {{}}}},
          ],
          "edges": [
            {{"source": "node_id", "target": "node_id", 
              "type": "RELATIONSHIP_TYPE", "properties": {{}}}},
          ]
        }}
        
        Text: {doc_text[:4000]}"""
        
        response = self.gemini_pro.generate_content(prompt)
        gemini_kg = self._parse_kg_json(response.text)
        
        # Step 3: Merge NLP entities with Gemini graph
        merged = self._merge_extractions(nl_entities, gemini_kg)
        
        # Step 4: Entity resolution (deduplicate similar entities)
        resolved = self._resolve_entities(merged)
        
        # Step 5: Write to Spanner Graph + BigQuery
        self._write_to_spanner_graph(resolved, doc_id)
        self._write_to_bigquery(resolved, doc_id)
        
        return resolved
    
    def query_graph_nl(self, question: str, graph_id: str) -> GraphQueryResult:
        """Convert natural language to GQL (Graph Query Language)"""
        schema = self.get_graph_schema(graph_id)
        
        prompt = f"""Convert this natural language question to a Spanner Graph Query.
        
        Graph Schema: {schema}
        Question: {question}
        
        Return ONLY the GQL query, nothing else."""
        
        gql = self.gemini_flash.generate_content(prompt).text
        results = self.spanner_graph.execute_query(gql)
        return GraphQueryResult(gql=gql, nodes=results.nodes, edges=results.edges)
```

**Spanner Graph Setup:**
```sql
-- Create graph schema in Spanner
CREATE TABLE KGNodes (
  NodeId STRING(MAX) NOT NULL,
  GraphId STRING(MAX) NOT NULL,
  EntityType STRING(100),
  EntityName STRING(MAX),
  Properties JSON,
) PRIMARY KEY (GraphId, NodeId);

CREATE TABLE KGEdges (
  EdgeId STRING(MAX) NOT NULL,
  GraphId STRING(MAX) NOT NULL,
  SourceNodeId STRING(MAX),
  TargetNodeId STRING(MAX),
  RelationshipType STRING(100),
  Properties JSON,
) PRIMARY KEY (GraphId, EdgeId),
  INTERLEAVE IN PARENT KGNodes ON DELETE CASCADE;

CREATE PROPERTY GRAPH EnterpriseKG
  NODE TABLES (KGNodes)
  EDGE TABLES (KGEdges
    SOURCE KEY (SourceNodeId) REFERENCES KGNodes (NodeId)
    DESTINATION KEY (TargetNodeId) REFERENCES KGNodes (NodeId)
  );
```

- [ ] Implement full KG extraction pipeline
- [ ] Set up Spanner Graph schema and client
- [ ] Build entity resolution (merge duplicate entities across documents)
- [ ] Implement GQL generation from natural language
- [ ] Build cross-document relationship detection
- [ ] Deploy as `ml-kg-service` on Cloud Run
- [ ] Build KG evaluation metrics (precision, recall of entity extraction)

---

### 📅 Months 7–9 — MLOps & Advanced Features

- [ ] Set up Vertex AI Model Registry (version all deployed models)
- [ ] Implement model drift detection (monitor feature distributions)
- [ ] Automated retraining pipelines with Cloud Composer
- [ ] A/B testing framework for Gemini prompt versions
- [ ] Implement RAG feedback loop (thumbs up/down → fine-tuning data)
- [ ] Multi-modal RAG (images + text in documents — Gemini Vision)
- [ ] Implement Gemini context caching for large document corpora
- [ ] Advanced anomaly root cause analysis using Gemini
- [ ] Hierarchical forecasting (aggregate + disaggregate levels)
- [ ] Knowledge graph temporal evolution (track changes over time)

---

### 📅 Months 10–12 — Production Hardening

- [ ] Gemini grounding with Google Search (hybrid internal + web knowledge)
- [ ] Fine-tune embedding model on domain-specific data (Vertex AI)
- [ ] Implement model explainability for anomaly predictions
- [ ] Complete MLOps documentation (model cards, data sheets)
- [ ] Cost optimization (Gemini Flash vs Pro routing based on query complexity)
- [ ] Batch prediction jobs for scheduled anomaly scans
- [ ] Load testing ML services at 10x scale
- [ ] Model performance benchmarks and SLA compliance reports

---

## 8. Person C — Frontend & UX Engineer Roadmap

### Overview
Person C builds the entire user-facing experience. Works against mock APIs from Day 1 and switches to real APIs as Person A delivers them.

---

### 📅 Month 1 — Project Setup & Design System

**Week 1-2: Environment Setup**
- [ ] Initialize Next.js 14 project with App Router and TypeScript
  ```bash
  npx create-next-app@latest enterpriseiq-frontend \
    --typescript --tailwind --eslint --app --src-dir
  ```
- [ ] Install and configure shadcn/ui component library
- [ ] Set up Tailwind CSS design tokens:
  ```javascript
  // tailwind.config.ts
  colors: {
    brand: { 50: '#f0f4ff', 500: '#4F46E5', 900: '#1e1b4b' },
    gemini: { 400: '#4285F4', 500: '#1A73E8' },
  }
  ```
- [ ] Set up API client with mock server base URL
- [ ] Configure Firebase Auth SDK
- [ ] Set up Storybook for component development
- [ ] Set up Jest + React Testing Library + Playwright

**Week 3-4: Authentication & Shell**
- [ ] Build Sign-In page (Google SSO via Firebase + email/password)
  ```typescript
  // Google SSO with Firebase
  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();
    // Send token to backend for session creation
    await apiClient.post('/v1/auth/session', { idToken });
  };
  ```
- [ ] Build App Shell (sidebar, header, navigation)
- [ ] Build Workspace selector (multi-tenant)
- [ ] Build Settings page (API keys, notifications, preferences)
- [ ] Set up Zustand global state management
- [ ] Configure SWR for data fetching with optimistic updates

---

### 📅 Month 2 — RAG Chat Interface

**RAG Chat UI:**
```typescript
// components/rag/ChatInterface.tsx
'use client';
import { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}

export function ChatInterface({ corpusId }: { corpusId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  
  const sendMessage = async () => {
    const userMsg = { role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setStreaming(true);
    
    // Server-Sent Events for streaming
    const response = await fetch('/api/rag/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: input, corpus_id: corpusId })
    });
    
    const reader = response.body?.getReader();
    let assistantMsg = { role: 'assistant', content: '', sources: [], timestamp: new Date() };
    
    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;
      const chunk = new TextDecoder().decode(value);
      assistantMsg.content += chunk;
      setMessages(prev => [...prev.slice(0, -1), { ...assistantMsg }]);
    }
    setStreaming(false);
  };
  
  return (
    <div className="flex flex-col h-full">
      <MessageList messages={messages} />
      <SourceCitations sources={messages.at(-1)?.sources} />
      <ChatInput value={input} onChange={setInput} onSend={sendMessage} />
    </div>
  );
}
```

**Features to Build:**
- [ ] Real-time streaming chat with Gemini (Server-Sent Events)
- [ ] Document upload UI (drag-and-drop, progress bar, file type icons)
- [ ] Corpus management (create, list, delete document collections)
- [ ] Source citation display (highlighted text with document links)
- [ ] Conversation history (saved to Firestore, paginated)
- [ ] Suggested questions (Gemini-generated from corpus)
- [ ] Multi-corpus query (select multiple sources at once)
- [ ] Copy answer button, thumbs up/down feedback

---

### 📅 Month 3 — Data Pipeline Monitor

**Pipeline Dashboard:**
- [ ] Pipeline list view (status indicators: running, success, failed, scheduled)
- [ ] Pipeline detail view (steps, records processed, duration, error logs)
- [ ] Real-time pipeline progress (WebSocket updates)
- [ ] Create Pipeline wizard (step-by-step: source → transform → destination)
- [ ] Pipeline schedule editor (cron expression builder UI)
- [ ] Error records viewer (browse invalid records with reasons)
- [ ] Pipeline run history (table with sorting, filtering)
- [ ] Manual trigger button with confirmation dialog

```typescript
// components/pipeline/PipelineCard.tsx
export function PipelineCard({ pipeline }: { pipeline: Pipeline }) {
  const statusColor = {
    running: 'text-blue-500',
    success: 'text-green-500',
    failed: 'text-red-500',
    scheduled: 'text-yellow-500'
  }[pipeline.status];
  
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">{pipeline.name}</h3>
          <p className={`text-sm ${statusColor}`}>{pipeline.status}</p>
        </div>
        <ProgressRing value={pipeline.completion_pct} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-sm text-gray-500">
        <span>{pipeline.records_processed?.toLocaleString()} records</span>
        <span>{pipeline.duration_human}</span>
        <span>{pipeline.next_run_human}</span>
      </div>
    </div>
  );
}
```

---

### 📅 Month 4 — Analytics Agent UI

**Natural Language Query Interface:**
```typescript
// components/analytics/NLQueryInterface.tsx
export function NLQueryInterface({ datasetId }: { datasetId: string }) {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  
  const exampleQuestions = [
    "What were the top 5 products by revenue last month?",
    "Show me daily user signups for the past 30 days",
    "Which regions had the highest churn rate in Q3?"
  ];
  
  return (
    <div className="space-y-6">
      {/* Question Input */}
      <div className="relative">
        <SparklesIcon className="absolute left-3 top-3 text-indigo-500" />
        <textarea
          className="w-full rounded-xl border-2 border-indigo-200 pl-10 pr-4 py-3"
          placeholder="Ask anything about your data..."
          value={question}
          onChange={e => setQuestion(e.target.value)}
        />
        <Button onClick={handleQuery} className="absolute right-3 bottom-3">
          Analyze →
        </Button>
      </div>
      
      {/* Example chips */}
      <div className="flex flex-wrap gap-2">
        {exampleQuestions.map(q => (
          <button key={q} onClick={() => setQuestion(q)}
            className="rounded-full bg-indigo-50 px-3 py-1 text-sm text-indigo-600">
            {q}
          </button>
        ))}
      </div>
      
      {/* Results */}
      {result && (
        <div className="space-y-4">
          <SqlCodeBlock sql={result.sql_generated} />
          <DynamicChart type={result.chart_suggestion} data={result.results} />
          <ExplanationCard text={result.explanation} />
          <DataTable data={result.results} />
        </div>
      )}
    </div>
  );
}
```

**Features:**
- [ ] Natural language question input with AI suggestions
- [ ] Auto-rendered charts based on query type (Recharts)
- [ ] SQL query display with syntax highlighting
- [ ] Interactive data table with sorting, filtering, export
- [ ] Query history (last 50 queries per user)
- [ ] Dataset selector (choose which BQ tables to query)
- [ ] Share query result as link
- [ ] Export results as CSV / JSON

---

### 📅 Month 5 — Anomaly Detection Dashboard

**Anomaly Dashboard:**
```typescript
// components/anomaly/AnomalyDashboard.tsx
export function AnomalyDashboard({ datasetId }: Props) {
  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Summary cards */}
      <SummaryCard title="Total Anomalies" value={42} delta={-12} className="col-span-3" />
      <SummaryCard title="Critical" value={3} color="red" className="col-span-3" />
      <SummaryCard title="Unacknowledged" value={15} color="yellow" className="col-span-3" />
      <SummaryCard title="Avg Score" value="0.87" className="col-span-3" />
      
      {/* Time-series chart with anomaly markers */}
      <div className="col-span-8">
        <AnomalyTimeSeriesChart datasetId={datasetId} />
      </div>
      
      {/* Anomaly list */}
      <div className="col-span-4">
        <AnomalyList datasetId={datasetId} />
      </div>
      
      {/* Severity heatmap */}
      <div className="col-span-12">
        <AnomalyHeatmap datasetId={datasetId} />
      </div>
    </div>
  );
}
```

**Features:**
- [ ] Time-series chart with anomaly markers (Recharts)
- [ ] Anomaly severity heatmap (D3.js calendar heatmap)
- [ ] Anomaly list with severity badges and acknowledge button
- [ ] Anomaly detail modal (value, expected range, Gemini explanation)
- [ ] Real-time anomaly alerts (WebSocket — new anomalies pop up in-app)
- [ ] Anomaly sensitivity slider (low / medium / high)
- [ ] Bulk acknowledge UI
- [ ] Alert rules editor (configure thresholds per metric)
- [ ] Email/Slack notification preference per alert rule

---

### 📅 Month 6 — Forecasting Charts + Integration Sprint

**Forecasting UI:**
```typescript
// components/forecast/ForecastChart.tsx
import { ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ReferenceLine } from 'recharts';

export function ForecastChart({ forecastId }: { forecastId: string }) {
  const { data } = useForecast(forecastId);
  
  // Merge historical + forecast data
  const chartData = [...data.historical, ...data.forecast].map(d => ({
    date: d.timestamp,
    actual: d.actual_value,
    predicted: d.predicted_value,
    lower: d.lower_bound,
    upper: d.upper_bound,
    isForecast: d.is_forecast
  }));
  
  return (
    <div className="rounded-xl border bg-white p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold">{data.target_column} Forecast</h3>
        <ForecastHorizonSelector />
      </div>
      
      <ComposedChart data={chartData} height={300}>
        <Area dataKey="upper" fill="#E8F0FE" strokeWidth={0} />
        <Area dataKey="lower" fill="#ffffff" strokeWidth={0} />
        <Line dataKey="actual" stroke="#1A73E8" strokeWidth={2} dot={false} />
        <Line dataKey="predicted" stroke="#34A853" strokeWidth={2} 
              strokeDasharray="5 5" dot={false} />
        <ReferenceLine x={data.forecast_start_date} stroke="#9AA0A6" 
                       label="Forecast Start" strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip content={<CustomTooltip />} />
      </ComposedChart>
      
      <GeminiForecastExplanation explanation={data.explanation} />
    </div>
  );
}
```

**Features:**
- [ ] Forecast chart: historical + predicted + confidence band
- [ ] Forecast horizon selector (7d / 30d / 90d / 180d)
- [ ] Model selector (AutoML vs Prophet)
- [ ] Gemini plain-English forecast explanation card
- [ ] Seasonality decomposition view (trend + weekly + yearly)
- [ ] Forecast accuracy metrics (MAE, RMSE, MAPE badges)
- [ ] Export forecast as CSV / schedule report

**Integration Sprint (Month 6):**
- [ ] Switch all API calls from mock server to real staging APIs (Person A)
- [ ] Implement error states for all API failures
- [ ] Add loading skeletons everywhere
- [ ] End-to-end Playwright tests for all major flows
- [ ] Fix UI bugs discovered in integration

---

### 📅 Month 7 — Knowledge Graph Visualizer

**Interactive Knowledge Graph Explorer:**
```typescript
// components/kg/KnowledgeGraphViewer.tsx
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';

cytoscape.use(fcose);

export function KnowledgeGraphViewer({ graphId }: Props) {
  const [elements, setElements] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nlQuery, setNlQuery] = useState('');
  
  const cytoscapeStylesheet = [
    { selector: 'node[type="PERSON"]', 
      style: { backgroundColor: '#4285F4', label: 'data(label)', color: '#fff' } },
    { selector: 'node[type="ORG"]', 
      style: { backgroundColor: '#34A853', shape: 'rectangle' } },
    { selector: 'node[type="PRODUCT"]', 
      style: { backgroundColor: '#FBBC05', shape: 'diamond' } },
    { selector: 'edge',
      style: { 
        label: 'data(relationshipType)',
        lineColor: '#9AA0A6',
        targetArrowColor: '#9AA0A6',
        targetArrowShape: 'triangle',
        curveStyle: 'bezier'
      }
    }
  ];
  
  return (
    <div className="flex h-full">
      {/* Graph Canvas */}
      <div className="flex-1 relative">
        <CytoscapeComponent
          elements={elements}
          stylesheet={cytoscapeStylesheet}
          layout={{ name: 'fcose', animate: true }}
          cy={cy => {
            cy.on('tap', 'node', e => setSelectedNode(e.target.data()));
          }}
        />
        <GraphControls onZoomIn={} onZoomOut={} onReset={} />
        <NLQueryBar value={nlQuery} onChange={setNlQuery} onQuery={handleNLQuery} />
      </div>
      
      {/* Side panel */}
      <div className="w-80 border-l p-4">
        {selectedNode ? 
          <EntityDetailPanel entity={selectedNode} onExpand={expandNode} /> :
          <GraphStatsPanel graphId={graphId} />
        }
      </div>
    </div>
  );
}
```

**Features:**
- [ ] Interactive force-directed graph (Cytoscape.js with fCoSE layout)
- [ ] Entity type color coding and shape icons
- [ ] Click node → expand neighborhood (load more edges)
- [ ] Natural language graph query ("Show all people who work at Google")
- [ ] Relationship type filter sidebar
- [ ] Path finder (shortest path between two entities)
- [ ] Document source link (click entity → see which doc it came from)
- [ ] Graph statistics panel (node count, edge count, top entities)
- [ ] Export graph as PNG / JSON

---

### 📅 Months 8–9 — Polish, Looker Studio & Performance

**Looker Studio Embedded Reports:**
```typescript
// Embed Looker Studio reports in the app
export function EmbeddedLookerReport({ reportId, params }: Props) {
  const embedUrl = `https://lookerstudio.google.com/embed/reporting/${reportId}`;
  const queryParams = new URLSearchParams(params).toString();
  
  return (
    <iframe
      src={`${embedUrl}?${queryParams}`}
      className="w-full rounded-xl border"
      style={{ height: '600px' }}
      allowFullScreen
    />
  );
}
```

- [ ] Embed pre-built Looker Studio reports for executive dashboards
- [ ] Build unified Home Dashboard (summary of all 5 modules)
- [ ] Implement global search (search across documents, queries, anomalies)
- [ ] Add dark mode support
- [ ] Build notification center (in-app notification bell)
- [ ] Implement keyboard shortcuts (Cmd+K command palette)
- [ ] Accessibility audit (WCAG 2.1 AA compliance)
- [ ] Performance optimization (Core Web Vitals: LCP < 2.5s)
- [ ] Progressive Web App (PWA) manifest + service worker

---

### 📅 Months 10–12 — Mobile, Final Polish, Launch

- [ ] Mobile-responsive optimization (all views work on 375px width)
- [ ] Onboarding flow (first-time user guided tour)
- [ ] In-app help center (embedded documentation)
- [ ] User feedback collection (NPS survey component)
- [ ] Analytics (Google Analytics 4 integration)
- [ ] Complete Storybook documentation for all components
- [ ] Accessibility fixes from audit
- [ ] Final Playwright E2E test suite (100% critical path coverage)
- [ ] Firebase Hosting deployment pipeline (automated via Cloud Build)
- [ ] Performance budget enforcement (Lighthouse CI in GitHub Actions)

---

## 9. Combined Monthly Timeline

```
MONTH │ PERSON A (Backend/Data) │ PERSON B (ML/AI)          │ PERSON C (Frontend)
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  1   │ GCP setup, Terraform,   │ Vertex AI setup,          │ Next.js setup, design   
      │ BQ schemas, Mock API,   │ RAG research, embedding   │ system, Auth, App Shell  
      │ Firebase Auth           │ benchmarks                │                         
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  2   │ Dataflow pipelines      │ RAG engine: Vector Search │ RAG Chat UI, doc upload,
      │ (doc ingestion,         │ + Gemini, streaming,      │ corpus management,      
      │ validator, connector)   │ hybrid search             │ SSE streaming           
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  3   │ RAG backend APIs,       │ Anomaly detection models  │ Pipeline Monitor UI,    
      │ GCS + Dataflow wiring,  │ (stat + Isolation Forest  │ pipeline wizard,        
      │ Redis cache, rate limit │ + Vertex AI), alerting    │ real-time progress      
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  4   │ Agent + Anomaly APIs,   │ Forecasting (AutoML +     │ NL Query UI, dynamic   
      │ SQL safety, BQ result   │ Prophet), model training, │ charts, SQL viewer,     
      │ caching, dataset reg.   │ Vertex AI deploy          │ query history           
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  5   │ KG APIs, WebSocket,     │ Analytics Agent (Gemini   │ Anomaly Dashboard,     
      │ notifications, Spanner  │ function calling,         │ time-series charts,    
      │ Graph, security         │ NL-to-SQL agentic loop)   │ heatmap, alerts UI     
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  6   │ Integration sprint,     │ KG extraction (Gemini +   │ Forecast Charts,       
      │ performance tests,      │ Cloud NLP, Spanner Graph  │ INTEGRATION SPRINT:    
      │ API docs, BQ optimize   │ write), deploy all svcs   │ switch mock → real API 
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  7   │ Streaming analytics,    │ MLOps: model registry,    │ Knowledge Graph        
      │ data lineage, multi-    │ drift detection, auto     │ Visualizer (Cytoscape),
      │ region failover         │ retraining Composer DAGs  │ graph explorer         
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  8   │ GraphQL API, export API,│ Multi-modal RAG (Vision), │ Looker Studio embeds,  
      │ RBAC, column-level      │ Gemini context caching,   │ Home Dashboard,        
      │ security                │ A/B prompt testing        │ global search, dark mode
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
  9   │ API versioning (v2),    │ Advanced anomaly RCA,     │ Accessibility audit,   
      │ cost optimization,      │ hierarchical forecasting, │ PWA, keyboard shortcuts,
      │ load testing            │ KG temporal evolution     │ notification center    
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
 10   │ Google Workspace integr,│ Gemini Search grounding,  │ Mobile responsive,     
      │ webhooks, API analytics │ embedding fine-tuning,    │ onboarding flow,       
      │ dashboard               │ explainability            │ in-app help center     
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
 11   │ Tenant onboarding auto, │ Batch prediction jobs,    │ Analytics GA4,        
      │ SLA monitoring,         │ cost optimization (Flash  │ user feedback, NPS,    
      │ penetration testing     │ vs Pro routing)           │ Storybook docs         
──────┼─────────────────────────┼───────────────────────────┼─────────────────────────
 12   │ Final security audit,   │ Model performance report, │ E2E Playwright suite,  
      │ documentation, runbooks,│ MLOps documentation,      │ Lighthouse CI,         
      │ 10x load test           │ model cards, handoff      │ production deploy      
──────┴─────────────────────────┴───────────────────────────┴─────────────────────────

KEY MILESTONES:
  ★ End of Month 1  → Shared contracts done + Mock API live → All 3 unblocked
  ★ End of Month 3  → RAG end-to-end working (internal demo)
  ★ End of Month 6  → All 5 modules connected (integration milestone)
  ★ End of Month 9  → Beta release (internal users)
  ★ End of Month 12 → Production v1.0 release
```

---

## 10. Infrastructure & DevOps

### GCP Project Structure
```
enterpriseiq-dev     → Development environment
enterpriseiq-staging → Staging (mirrors prod)
enterpriseiq-prod    → Production
```

### Terraform Resources (Person A manages)
```hcl
# Main resources to provision

# BigQuery
resource "google_bigquery_dataset" "core" { dataset_id = "enterpriseiq_core" }
resource "google_bigquery_table" "documents" { ... }

# GCS Buckets
resource "google_storage_bucket" "raw_uploads" {
  name = "enterpriseiq-raw-uploads-${var.env}"
  lifecycle_rule { action { type = "Delete" } condition { age = 90 } }
}

# Cloud Run Services
resource "google_cloud_run_v2_service" "backend_api" {
  name = "enterpriseiq-api"
  template {
    scaling { min_instance_count = 2, max_instance_count = 20 }
    containers { image = "gcr.io/${var.project}/api:${var.image_tag}" }
  }
}

# Vertex AI Vector Search Index
resource "google_vertex_ai_index" "rag_index" {
  display_name = "enterpriseiq-rag"
  metadata {
    contents_delta_uri = "gs://..."
    config { dimensions = 768, approximate_neighbors_count = 10 }
  }
}

# Pub/Sub Topics
resource "google_pubsub_topic" "document_ingested" {
  name = "enterpriseiq.document.ingested"
}

# Spanner Instance + Database
resource "google_spanner_instance" "kg" { config = "regional-us-central1" }
resource "google_spanner_database" "kg" { name = "knowledge-graph" }
```

### CI/CD Pipeline (Cloud Build)
```yaml
# cloudbuild.yaml (runs on every PR merge)
steps:
  # Backend (Person A)
  - name: python:3.12
    id: test-backend
    dir: backend
    args: ['-m', 'pytest', 'tests/', '-v', '--cov']

  - name: gcr.io/cloud-builders/docker
    id: build-backend
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/api:$COMMIT_SHA', './backend']

  - name: gcr.io/cloud-builders/gcloud
    id: deploy-backend
    args: ['run', 'deploy', 'enterpriseiq-api',
           '--image', 'gcr.io/$PROJECT_ID/api:$COMMIT_SHA',
           '--region', 'us-central1']

  # ML Services (Person B)
  - name: python:3.12
    id: test-ml
    dir: ml
    args: ['-m', 'pytest', 'tests/', '-v']

  - name: gcr.io/cloud-builders/docker
    id: build-ml-rag
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ml-rag:$COMMIT_SHA', './ml/rag']

  # Frontend (Person C)
  - name: node:20
    id: test-frontend
    dir: frontend
    args: ['sh', '-c', 'npm ci && npm test && npm run build']

  - name: gcr.io/cloud-builders/firebase
    id: deploy-frontend
    args: ['deploy', '--only', 'hosting', '--project', '$PROJECT_ID']
```

### Monitoring & Alerting
```yaml
# Cloud Monitoring Alert Policies

alerts:
  - name: API Error Rate
    condition: error_rate > 1% for 5 minutes
    notification: PagerDuty + Slack

  - name: RAG Latency
    condition: p99_latency > 5s for 3 minutes
    notification: Slack

  - name: Dataflow Pipeline Failure
    condition: pipeline_status == FAILED
    notification: PagerDuty

  - name: Vertex AI Endpoint Errors
    condition: prediction_error_rate > 0.5%
    notification: Slack

  - name: BigQuery Cost
    condition: daily_bytes_processed > threshold
    notification: Email
```

---

## 11. Testing Strategy

### Person A — Backend Testing
```
Unit Tests (Pytest):
  - All API endpoint handlers
  - Data validation logic
  - BigQuery query builders
  - Pipeline step functions

Integration Tests:
  - API → BigQuery round-trip
  - API → GCS upload
  - Auth middleware with Firebase

Load Tests (Locust):
  Target: 1000 concurrent users, < 200ms p95 latency
  Scenarios: 60% read, 30% write, 10% ML calls
```

### Person B — ML Testing
```
Unit Tests:
  - Chunking logic (chunk size, overlap)
  - Embedding pipeline correctness
  - SQL safety validator
  - KG parsing functions

ML Evaluation:
  RAG:     RAGAS faithfulness > 0.85, relevancy > 0.80
  Anomaly: Precision > 0.90, Recall > 0.85 on labeled dataset
  Forecast: MAPE < 10% on test set
  KG:      Entity precision > 0.85, relation F1 > 0.75

Model Tests:
  - Regression tests on golden QA pairs
  - Prompt regression tests (ensure Gemini changes don't break outputs)
```

### Person C — Frontend Testing
```
Unit Tests (Jest + RTL):
  - All React components
  - Utility functions
  - API client functions

E2E Tests (Playwright):
  Critical paths:
    1. Sign in → Create corpus → Upload doc → Ask question → See answer
    2. Create pipeline → Trigger → See results
    3. Ask NL question → See chart → Export CSV
    4. View anomalies → Acknowledge → Set alert rule
    5. Run forecast → View chart → Read explanation

Visual Regression (Playwright screenshots):
  - Dashboard at different viewport sizes
  - Dark mode vs light mode

Performance (Lighthouse CI):
  - LCP < 2.5s, FID < 100ms, CLS < 0.1
  - Bundle size < 500KB initial
```

---

## 12. Milestone Deliverables

### 🏁 Milestone 1: End of Month 3
- [ ] Mock API replaced by real backend (Person A)
- [ ] RAG: Upload document, ask question, get cited answer
- [ ] Pipeline: Ingest CSV from GCS, validate, load to BigQuery
- [ ] Auth: Google SSO working end-to-end

### 🏁 Milestone 2: End of Month 6 — Integration Complete
- [ ] All 5 modules have working end-to-end flows
- [ ] All 3 layers connected (frontend → backend → ML)
- [ ] Anomaly detection demo with real dataset
- [ ] Forecasting chart with confidence band
- [ ] Basic knowledge graph extracted from 10 documents

### 🏁 Milestone 3: End of Month 9 — Beta Release
- [ ] Multi-tenant workspace support
- [ ] Real-time WebSocket anomaly alerts
- [ ] Analytics agent with 5+ query types
- [ ] Knowledge graph explorer (cytoscape, NL queries)
- [ ] Pipeline monitoring dashboard
- [ ] 95% unit test coverage, all E2E tests passing

### 🏁 Milestone 4: End of Month 12 — Production v1.0
- [ ] All enterprise security features (RBAC, audit logs, data isolation)
- [ ] 99.9% uptime SLA infrastructure
- [ ] Full documentation (API docs, user guide, runbooks)
- [ ] Passed security audit and penetration test
- [ ] Loaded to 10x projected scale without degradation
- [ ] MLOps: automated retraining, model monitoring, drift detection

---

## 13. Success Metrics & KPIs

### Technical KPIs
| Metric | Target |
|--------|--------|
| API p95 Latency | < 200ms (non-AI endpoints) |
| RAG Query p95 Latency | < 5 seconds |
| RAG Answer Faithfulness (RAGAS) | > 0.85 |
| Anomaly Detection Precision | > 90% |
| Anomaly Detection Recall | > 85% |
| Forecast MAPE | < 10% |
| KG Entity Extraction F1 | > 0.80 |
| NL-to-SQL Accuracy | > 85% (on test queries) |
| System Uptime | > 99.9% |
| Core Web Vitals (LCP) | < 2.5 seconds |
| API Test Coverage | > 95% |

### Business KPIs (after launch)
| Metric | Target (6 months post-launch) |
|--------|-------------------------------|
| Time to answer data question | < 30 seconds (vs hours) |
| Document ingestion throughput | > 1,000 docs/hour |
| Pipeline success rate | > 99% |
| Anomaly false positive rate | < 10% |
| User query satisfaction (thumbs up) | > 80% |
| Monthly active workspaces | 50+ |

---

## 📁 Repository Structure

```
enterpriseiq/
├── contracts/                    ← Shared by all 3 (never edited solo)
│   ├── openapi.yaml
│   ├── bigquery-schemas/
│   ├── event-schemas/
│   └── mock-server/              ← Person A maintains (Prism mock server)
│
├── backend/                      ← Person A
│   ├── app/
│   │   ├── api/v1/               ← Route handlers
│   │   ├── services/             ← Business logic
│   │   ├── models/               ← Pydantic schemas
│   │   └── clients/              ← BQ, GCS, Firestore, ML service clients
│   ├── pipelines/                ← Dataflow (Apache Beam) pipelines
│   ├── tests/
│   └── Dockerfile
│
├── ml/                           ← Person B
│   ├── rag/                      ← RAG engine service
│   ├── anomaly/                  ← Anomaly detection service
│   ├── forecast/                 ← Forecasting service
│   ├── agent/                    ← Analytics agent service
│   ├── kg/                       ← Knowledge graph service
│   ├── pipelines/                ← Vertex AI + Composer DAGs
│   ├── notebooks/                ← Vertex AI Workbench notebooks
│   └── tests/
│
├── frontend/                     ← Person C
│   ├── src/
│   │   ├── app/                  ← Next.js App Router pages
│   │   ├── components/           ← React components
│   │   ├── hooks/                ← Custom React hooks
│   │   ├── lib/                  ← API clients, utils
│   │   └── stores/               ← Zustand state stores
│   ├── tests/                    ← Jest + Playwright
│   └── public/
│
└── infrastructure/               ← Person A
    ├── terraform/
    │   ├── main.tf
    │   ├── bigquery.tf
    │   ├── gcs.tf
    │   ├── cloudrun.tf
    │   ├── vertexai.tf
    │   └── pubsub.tf
    └── cloudbuild.yaml
```

---

## 🔐 Security Checklist

- [ ] All service-to-service calls use Workload Identity (no static keys)
- [ ] BigQuery row-level security per workspace
- [ ] PII detection and masking in pipelines (DLP API)
- [ ] All data encrypted at rest (CMEK) and in transit (TLS 1.3)
- [ ] VPC Service Controls perimeter around BigQuery + GCS
- [ ] Cloud Armor WAF in front of API Gateway
- [ ] Audit logging of all data access to BigQuery
- [ ] Secret Manager for all credentials (no secrets in code)
- [ ] RBAC with least-privilege roles
- [ ] Vulnerability scanning in CI/CD (Container Analysis API)

---

> **Total Estimated Cloud Cost (Monthly at Scale):**
> Vertex AI Vector Search: ~$300 | BigQuery: ~$200 | Cloud Run: ~$150
> Gemini API (Pro + Flash): ~$400 | Dataflow: ~$100 | Others: ~$150
> **Total: ~$1,300/month at moderate usage (scales with data volume)**

---

*Document version: 1.0 | Created: May 2026 | Review cycle: Monthly*
*All three engineers should re-read Section 5 (Shared Contracts) before making any cross-cutting changes.*
