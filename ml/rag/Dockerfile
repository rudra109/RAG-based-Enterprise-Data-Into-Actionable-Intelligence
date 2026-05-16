# EnterpriseIQ ML — RAG Service Dockerfile
# Multi-stage build for minimal image size

FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# ── Production stage ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy service code
COPY shared/ ./shared/
COPY rag/ ./rag/

# Create non-root user for security
RUN useradd -m -u 1000 mlservice && chown -R mlservice:mlservice /app
USER mlservice

# Cloud Run requires port 8080
ENV PORT=8001
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start RAG service
CMD ["uvicorn", "rag.main:app", "--host", "0.0.0.0", "--port", "8001", \
     "--workers", "4"]
