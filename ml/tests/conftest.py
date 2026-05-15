"""
EnterpriseIQ ML — Test Configuration & Shared Fixtures
conftest.py is picked up automatically by pytest for all test files.
"""

from __future__ import annotations

import sys
import os

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
# Add ml/ root to sys.path so all imports work from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Environment setup for tests ───────────────────────────────────────────────
# Override settings to use test values (no real GCP calls)
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("GCP_REGION", "us-central1")
os.environ.setdefault("GEMINI_PRO_MODEL", "gemini-1.5-pro")
os.environ.setdefault("GEMINI_FLASH_MODEL", "gemini-1.5-flash")
os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-004")
os.environ.setdefault("BIGQUERY_DATASET", "test_dataset")
os.environ.setdefault("BIGQUERY_PROJECT", "test-project")
os.environ.setdefault("SPANNER_INSTANCE_ID", "test-instance")
os.environ.setdefault("SPANNER_DATABASE_ID", "test-db")
os.environ.setdefault("VERTEX_AI_INDEX_ID", "test-index")
os.environ.setdefault("VERTEX_AI_INDEX_ENDPOINT_ID", "test-endpoint")


# ── Shared sample data fixtures ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_text_document():
    return """
    Acme Corporation Q3 2024 Earnings Report
    
    Revenue Performance:
    Total revenue reached $4.2 billion in Q3 2024, representing a 15% year-over-year increase.
    North America contributed $2.1 billion, while International markets added $2.1 billion.
    
    Key Developments:
    - CEO John Smith announced a strategic partnership with TechCorp Inc.
    - CFO Jane Doe confirmed guidance for Q4 2024 remains at $4.5-4.7 billion.
    - Product XYZ launched in 15 new markets across Europe and Asia-Pacific.
    
    Risk Factors:
    Management identified supply chain disruption, regulatory changes in the EU,
    and foreign exchange headwinds as primary risk factors for the remainder of 2024.
    
    Sustainability:
    Acme achieved carbon neutrality in North America operations and committed to
    global carbon neutrality by 2030.
    """


@pytest.fixture(scope="session")
def sample_time_series_data():
    """Generate synthetic time series for forecasting tests."""
    import pandas as pd
    import numpy as np

    dates = pd.date_range("2023-01-01", periods=365, freq="D")
    values = (
        100
        + np.arange(365) * 0.5
        + np.sin(np.arange(365) * 2 * np.pi / 7) * 10   # weekly seasonality
        + np.sin(np.arange(365) * 2 * np.pi / 365) * 20  # yearly seasonality
        + np.random.default_rng(42).normal(0, 3, 365)
    )
    return pd.DataFrame({"timestamp": dates, "revenue": values})


@pytest.fixture(scope="session")
def sample_anomaly_dataset():
    """Dataset with injected anomalies for testing."""
    import pandas as pd
    import numpy as np

    rng = np.random.default_rng(42)
    n = 500
    values = rng.normal(100, 10, n)

    # Inject anomalies at known indices
    anomaly_indices = [50, 150, 250, 350, 450]
    for idx in anomaly_indices:
        values[idx] = rng.choice([500.0, -200.0])

    dates = pd.date_range("2024-01-01", periods=n, freq="H")
    return {
        "df": pd.DataFrame({"timestamp": dates, "value": values}),
        "known_anomaly_indices": anomaly_indices,
    }


@pytest.fixture(scope="session")
def sample_kg_json_response():
    """Valid Gemini KG extraction response for testing."""
    return {
        "nodes": [
            {"id": "n1", "type": "ORG", "name": "Acme Corporation", "properties": {"sector": "tech"}},
            {"id": "n2", "type": "PERSON", "name": "John Smith", "properties": {"role": "CEO"}},
            {"id": "n3", "type": "PERSON", "name": "Jane Doe", "properties": {"role": "CFO"}},
            {"id": "n4", "type": "ORG", "name": "TechCorp Inc", "properties": {}},
        ],
        "edges": [
            {"source": "n2", "target": "n1", "type": "CEO_OF", "properties": {}},
            {"source": "n3", "target": "n1", "type": "CFO_OF", "properties": {}},
            {"source": "n1", "target": "n4", "type": "PARTNERED_WITH", "properties": {}},
        ],
    }
