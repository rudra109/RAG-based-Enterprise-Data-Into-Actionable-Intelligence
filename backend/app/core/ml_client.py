"""
EnterpriseIQ Backend — ML Service HTTP Client
Proxy client that calls Developer B's internal ML microservices.
Field mappings are aligned with Developer B's actual request/response schemas.
"""

from __future__ import annotations

import structlog
import httpx
from typing import Any

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class MLServiceClient:
    """Async HTTP client for Developer B's ML services."""

    def __init__(self, timeout: float = 120.0) -> None:
        self._timeout = timeout

    async def _post(self, url: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def _get(self, url: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    # ── RAG Service ─────────────────────────────────────────────────────────
    # Developer B schema: RAGQueryRequest { question, corpus_id, top_k, use_hybrid, session_id }
    # Developer B response: RAGResponse { answer, sources, confidence, ... }

    async def rag_query(self, question: str, corpus_id: str, top_k: int = 5) -> dict:
        url = f"{settings.rag_service_url}/internal/rag/query"
        logger.info("Calling RAG service", url=url, corpus_id=corpus_id)
        result = await self._post(url, {
            "question": question,
            "corpus_id": corpus_id,
            "top_k": top_k,
            "use_hybrid": True,
        })
        # Normalize response field names for backend layer
        return {
            "answer": result.get("answer", ""),
            "sources": [
                {
                    "chunk_id": s.get("chunk_id", ""),
                    "doc_id": s.get("doc_id", ""),
                    "text": s.get("chunk_text", s.get("text", "")),
                    "page_number": s.get("page_number"),
                    "score": s.get("score", 0.0),
                }
                for s in result.get("sources", [])
            ],
            "confidence": result.get("confidence", 0.0),
        }

    async def rag_embed_chunks(self, corpus_id: str, doc_id: str, chunks: list[str], chunk_ids: list[str]) -> dict:
        url = f"{settings.rag_service_url}/internal/rag/embed"
        return await self._post(url, {
            "corpus_id": corpus_id,
            "chunks": chunks,
            "chunk_ids": chunk_ids,
        })

    # ── Anomaly Service ─────────────────────────────────────────────────────
    # Developer B schema: DetectRequest { dataset_id, table, time_column, metric_columns, sensitivity, ... }
    # Developer B response: DetectResponse { dataset_id, total_records, anomaly_count, anomalies: [AnomalyItem] }
    # AnomalyItem: { anomaly_id, index, metric_name, actual_value, anomaly_score, severity, method, reason }

    async def anomaly_detect(
        self,
        dataset_id: str,
        time_column: str,
        metric_columns: list[str],
        sensitivity: str = "medium",
        table: str = "metrics",
    ) -> dict:
        url = f"{settings.anomaly_service_url}/internal/anomaly/detect"
        logger.info("Calling Anomaly service", url=url, dataset_id=dataset_id)
        result = await self._post(url, {
            "dataset_id": dataset_id,
            "table": table,
            "time_column": time_column,
            "metric_columns": metric_columns,
            "sensitivity": sensitivity,
            "use_statistical": True,
            "use_ml": True,
            "use_semantic": False,
        })
        # Normalize response
        return {
            "job_id": f"anomaly-{dataset_id}",
            "anomalies": [
                {
                    "anomaly_id": a.get("anomaly_id", ""),
                    "dataset_id": dataset_id,
                    "detected_at": str(result.get("generated_at", "")),
                    "metric_name": a.get("metric_name", ""),
                    "anomaly_score": float(a.get("anomaly_score", 0)),
                    "actual_value": float(a.get("actual_value", 0)),
                    "expected_value": None,
                    "lower_bound": None,
                    "upper_bound": None,
                    "is_acknowledged": False,
                    "severity": a.get("severity", "medium"),
                }
                for a in result.get("anomalies", [])
            ],
        }

    # ── Forecast Service ─────────────────────────────────────────────────────
    # Developer B schema: ForecastRequest { dataset_id, table, target_column, horizon_days, confidence_level, force_model }
    # Developer B response: ForecastResponse { forecast_id, predictions: [PredictionPoint { ds, yhat, yhat_lower, yhat_upper }], model_used }

    async def forecast_run(
        self,
        dataset_id: str,
        target_column: str,
        horizon_days: int,
        confidence_level: float = 0.95,
        table: str = "time_series",
    ) -> dict:
        url = f"{settings.forecast_service_url}/internal/forecast/run"
        logger.info("Calling Forecast service", url=url, dataset_id=dataset_id)
        result = await self._post(url, {
            "dataset_id": dataset_id,
            "table": table,
            "target_column": target_column,
            "horizon_days": horizon_days,
            "confidence_level": confidence_level,
        })
        # Normalize: Developer B uses "predictions", backend expects "forecast"
        return {
            "forecast_id": result.get("forecast_id", ""),
            "forecast": result.get("predictions", []),
            "model_version": result.get("model_used", "1.0"),
        }

    # ── Analytics Agent Service ─────────────────────────────────────────────
    # Developer B schema: AgentQueryRequest { question, dataset_id, session_id }
    # Developer B response: AgentQueryResponse { sql_generated, chart_suggestion, explanation, ... }
    # NOTE: Developer B's agent runs SQL internally. Backend re-runs for safety.

    async def agent_nl2sql(self, question: str, schema: dict, dataset_id: str = "") -> dict:
        url = f"{settings.agent_service_url}/internal/agent/nl2sql"
        logger.info("Calling Agent NL2SQL service", url=url)
        result = await self._post(url, {
            "question": question,
            "dataset_id": dataset_id,
            # Pass schema as part of the question context (Developer B's agent fetches schema itself)
        })
        # Normalize response field names
        return {
            "sql": result.get("sql_generated", ""),
            "chart_type": result.get("chart_suggestion", "table"),
            "explanation": result.get("explanation", ""),
        }

    # ── Knowledge Graph Service ─────────────────────────────────────────────
    # Developer B schema: ExtractRequest { doc_text, doc_id, graph_id }
    # For multi-doc extraction, we call once per document

    async def kg_extract(self, document_ids: list[str], graph_id: str, doc_texts: dict[str, str] | None = None) -> dict:
        url = f"{settings.kg_service_url}/internal/kg/extract"
        logger.info("Calling KG Extraction service", url=url, graph_id=graph_id)

        all_nodes, all_edges = [], []
        if doc_texts:
            for doc_id in document_ids:
                text = doc_texts.get(doc_id, f"Document {doc_id}")
                result = await self._post(url, {"doc_text": text, "doc_id": doc_id, "graph_id": graph_id})
                all_nodes.extend([{
                    "node_id": n.get("node_id", ""),
                    "entity_type": n.get("entity_type", ""),
                    "entity_name": n.get("entity_name", ""),
                    "properties": {},
                    "confidence": n.get("confidence", 0.9),
                    "source_doc_id": doc_id,
                } for n in result.get("nodes", [])])
                all_edges.extend([{
                    "edge_id": e.get("edge_id", ""),
                    "source_node_id": e.get("source_node_id", ""),
                    "target_node_id": e.get("target_node_id", ""),
                    "relationship_type": e.get("relationship_type", ""),
                    "properties": {},
                    "confidence": 0.9,
                    "source_doc_id": doc_id,
                } for e in result.get("edges", [])])

        return {
            "status": "processing" if not doc_texts else "completed",
            "nodes": all_nodes,
            "edges": all_edges,
        }

    async def kg_query(self, graph_id: str, query: str, query_type: str = "natural_language") -> dict:
        url = f"{settings.kg_service_url}/internal/kg/query"
        result = await self._post(url, {"question": query, "graph_id": graph_id})
        # Normalize to common schema
        return {
            "nodes": [
                {
                    "node_id": n.get("node_id", ""),
                    "entity_type": n.get("entity_type", ""),
                    "entity_name": n.get("entity_name", ""),
                    "properties": n.get("properties", {}),
                    "confidence": n.get("confidence", 0.9),
                }
                for n in result.get("nodes", [])
            ],
            "edges": [
                {
                    "edge_id": e.get("edge_id", ""),
                    "source_node_id": e.get("source_node_id", ""),
                    "target_node_id": e.get("target_node_id", ""),
                    "relationship_type": e.get("relationship_type", ""),
                    "properties": e.get("properties", {}),
                    "confidence": e.get("confidence", 0.9),
                }
                for e in result.get("edges", [])
            ],
            "explanation": result.get("gql", query),
        }

    async def kg_subgraph(self, entity_id: str, depth: int = 2, graph_id: str = "default") -> dict:
        url = f"{settings.kg_service_url}/internal/kg/subgraph"
        result = await self._post(url, {"entity_id": entity_id, "graph_id": graph_id, "depth": depth})
        return {
            "nodes": result.get("nodes", []),
            "edges": result.get("edges", []),
        }


# Singleton
_ml_client: MLServiceClient | None = None


def get_ml_client() -> MLServiceClient:
    global _ml_client
    if _ml_client is None:
        _ml_client = MLServiceClient()
    return _ml_client
