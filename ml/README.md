# EnterpriseIQ — ML & AI Intelligence Layer

## Developer B Workspace

This directory contains all ML/AI services for the EnterpriseIQ platform.

### Services
| Service | Port | Description |
|---------|------|-------------|
| `rag/` | 8001 | RAG Engine (Gemini + Vertex AI Vector Search) |
| `anomaly/` | 8002 | Anomaly Detection (Statistical + Isolation Forest + Gemini) |
| `forecast/` | 8003 | Forecasting (AutoML + Prophet) |
| `agent/` | 8004 | Analytics Agent (Gemini Function Calling NL-to-SQL) |
| `kg/` | 8005 | Knowledge Graph Extraction (Gemini + Cloud NLP + Spanner) |

### Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Fill in your GCP project, API keys, etc.

# 4. Run a service (e.g., RAG)
cd rag && uvicorn main:app --port 8001 --reload

# 5. Run all tests
pytest tests/ -v
```

### Environment Variables
See `.env.example` for all required variables.

### Architecture
All services communicate via internal HTTP (VPC-only). Person A's backend is the only external caller.
