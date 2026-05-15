"""
EnterpriseIQ — RAGAS Evaluation Notebook
Month 2 Research: Evaluate RAG pipeline quality on a golden QA dataset.
Run in Vertex AI Workbench.
"""

# %% Setup
import json
import pandas as pd
from google.cloud import bigquery
import vertexai

PROJECT_ID = "enterpriseiq-dev"
vertexai.init(project=PROJECT_ID, location="us-central1")
bq = bigquery.Client(project=PROJECT_ID)

# %% Define Golden QA Dataset
# These are hand-verified question-answer pairs for evaluation
GOLDEN_QA = [
    {
        "question": "What was total revenue in Q3 2024?",
        "ground_truth": "Total revenue in Q3 2024 was $4.2 billion.",
        "corpus_id": "annual_report_2024",
    },
    {
        "question": "What are the main risk factors?",
        "ground_truth": "Key risks include supply chain disruption, regulatory changes, and FX exposure.",
        "corpus_id": "annual_report_2024",
    },
    {
        "question": "Who is the current CFO?",
        "ground_truth": "The CFO is Jane Smith, appointed in January 2023.",
        "corpus_id": "org_chart_2024",
    },
]

# %% Run RAG against golden dataset
import sys
sys.path.insert(0, "../")
from rag.engine import EnterpriseRAGEngine

engine = EnterpriseRAGEngine()
results = []

for qa in GOLDEN_QA:
    response = engine.query(
        question=qa["question"],
        corpus_id=qa["corpus_id"],
        top_k=5,
        use_hybrid=True,
    )
    results.append({
        "question": qa["question"],
        "ground_truth": qa["ground_truth"],
        "answer": response.answer,
        "contexts": [s.text_snippet for s in response.sources],
        "confidence": response.confidence,
        "latency_ms": response.latency_ms,
    })

# %% RAGAS Evaluation
try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
    from datasets import Dataset

    dataset = Dataset.from_list([
        {
            "question": r["question"],
            "answer": r["answer"],
            "contexts": r["contexts"],
            "ground_truth": r["ground_truth"],
        }
        for r in results
    ])

    eval_result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
    )

    df = eval_result.to_pandas()
    print("\n=== RAGAS EVALUATION RESULTS ===")
    print(df[["question", "faithfulness", "answer_relevancy",
               "context_recall", "context_precision"]].to_string())

    print(f"\nMEAN SCORES:")
    for metric in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
        print(f"  {metric}: {df[metric].mean():.4f}")

    # Log to BigQuery
    rows = df.to_dict("records")
    bq.insert_rows_json("enterpriseiq-dev.enterpriseiq_core.rag_evaluations", rows)
    print("\n✅ Results logged to BigQuery")

except ImportError:
    print("RAGAS not installed. Run: pip install ragas")
    # Manual confidence-based evaluation
    df = pd.DataFrame(results)
    print(f"\nMean confidence: {df['confidence'].mean():.4f}")
    print(f"Mean latency: {df['latency_ms'].mean():.0f}ms")

# %% Chunking Strategy Comparison
print("\n=== CHUNKING STRATEGY COMPARISON ===")
from rag.chunking import FixedTokenChunker, SemanticChunker, RecursiveChunker

test_text = """
Enterprise data intelligence requires a sophisticated approach to information retrieval.
When organizations process thousands of documents daily, the chunking strategy becomes critical.

Fixed-size chunking is straightforward: split text into N-token windows with overlap.
This ensures predictable embedding dimensions and consistent retrieval performance.

Semantic chunking uses NLP to identify sentence boundaries, preserving semantic units.
This often leads to better retrieval quality at the cost of variable chunk sizes.

Recursive chunking attempts to split on natural boundaries (paragraphs, sentences)
before falling back to character-level splits for very long segments.
""" * 20

strategies = {
    "fixed": FixedTokenChunker(max_tokens=512, overlap_tokens=50),
    "semantic": SemanticChunker(max_tokens=512),
    "recursive": RecursiveChunker(max_tokens=512),
}

for name, chunker in strategies.items():
    chunks = chunker.chunk(test_text)
    avg_tokens = sum(c.token_count for c in chunks) / len(chunks) if chunks else 0
    print(f"\n{name.upper()}:")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Avg tokens: {avg_tokens:.0f}")
    print(f"  Min/Max tokens: {min(c.token_count for c in chunks)} / {max(c.token_count for c in chunks)}")
