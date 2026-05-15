"""
EnterpriseIQ ML — RAG Evaluation (RAGAS Metrics)
Logs faithfulness, relevancy, and context recall to BigQuery.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from shared.bigquery_client import BigQueryClient
from rag.schemas import RAGResponse

logger = structlog.get_logger(__name__)


class RAGEvaluator:
    """
    Wraps RAGAS metrics and logs evaluation results to BigQuery
    for offline analysis and continuous model improvement.
    """

    def __init__(self) -> None:
        self._bq = BigQueryClient()
        try:
            from ragas.metrics import faithfulness, answer_relevancy, context_recall
            self._metrics = {
                "faithfulness": faithfulness,
                "answer_relevancy": answer_relevancy,
                "context_recall": context_recall,
            }
            self._ragas_available = True
        except ImportError:
            logger.warning("RAGAS not available — evaluation logging disabled")
            self._ragas_available = False

    async def log_query_async(self, question: str, response: RAGResponse) -> None:
        """Non-blocking: compute and log RAGAS metrics."""
        try:
            record = {
                "eval_id": str(uuid.uuid4()),
                "question": question,
                "answer": response.answer,
                "source_count": len(response.sources),
                "confidence": response.confidence,
                "latency_ms": response.latency_ms,
                "model_used": response.model_used,
                "evaluated_at": datetime.utcnow().isoformat(),
                "faithfulness": None,
                "answer_relevancy": None,
            }

            if self._ragas_available and response.sources:
                contexts = [s.text_snippet for s in response.sources]
                try:
                    from ragas import evaluate
                    from datasets import Dataset
                    dataset = Dataset.from_dict({
                        "question": [question],
                        "answer": [response.answer],
                        "contexts": [contexts],
                    })
                    result = evaluate(dataset, metrics=list(self._metrics.values()))
                    record["faithfulness"] = float(result["faithfulness"])
                    record["answer_relevancy"] = float(result["answer_relevancy"])
                except Exception as e:
                    logger.warning("RAGAS evaluation failed", error=str(e))

            self._bq.insert_rows("rag_evaluations", [record])
            logger.debug("RAG evaluation logged", eval_id=record["eval_id"])
        except Exception as e:
            logger.error("Failed to log RAG evaluation", error=str(e))
