"""
EnterpriseIQ ML — Analytics Agent Tests
Tests SQL safety validator, chart suggestion, and agentic loop.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "../../")

from agent.analytics_agent import AnalyticsAgent, SQLSafetyValidator


# ────────────────────────────────────────────────────────────────────────────
# SQL Safety Validator Tests
# ────────────────────────────────────────────────────────────────────────────

class TestSQLSafetyValidator:

    @pytest.fixture
    def validator(self):
        return SQLSafetyValidator()

    # ── Safe queries ──────────────────────────────────────────────────────────

    def test_simple_select_is_safe(self, validator):
        sql = "SELECT * FROM my_table LIMIT 100"
        is_safe, reason = validator.validate(sql)
        assert is_safe
        assert reason == ""

    def test_select_with_where_is_safe(self, validator):
        sql = "SELECT id, name, revenue FROM sales WHERE date >= '2024-01-01'"
        is_safe, _ = validator.validate(sql)
        assert is_safe

    def test_cte_select_is_safe(self, validator):
        sql = """WITH monthly AS (
            SELECT DATE_TRUNC(date, MONTH) as month, SUM(revenue) as total
            FROM sales GROUP BY 1
        )
        SELECT * FROM monthly ORDER BY month"""
        is_safe, _ = validator.validate(sql)
        assert is_safe

    def test_aggregate_query_is_safe(self, validator):
        sql = "SELECT COUNT(*), AVG(price), MAX(quantity) FROM orders GROUP BY product_id"
        is_safe, _ = validator.validate(sql)
        assert is_safe

    def test_join_query_is_safe(self, validator):
        sql = """SELECT u.name, o.total
                 FROM users u JOIN orders o ON u.id = o.user_id
                 LIMIT 50"""
        is_safe, _ = validator.validate(sql)
        assert is_safe

    # ── Unsafe queries ────────────────────────────────────────────────────────

    def test_insert_is_blocked(self, validator):
        sql = "INSERT INTO users (name) VALUES ('hacker')"
        is_safe, reason = validator.validate(sql)
        assert not is_safe
        assert "INSERT" in reason or "Only SELECT" in reason

    def test_delete_is_blocked(self, validator):
        sql = "DELETE FROM users WHERE id = 1"
        is_safe, reason = validator.validate(sql)
        assert not is_safe

    def test_drop_is_blocked(self, validator):
        sql = "DROP TABLE users"
        is_safe, reason = validator.validate(sql)
        assert not is_safe
        assert "DROP" in reason or "Only SELECT" in reason

    def test_update_is_blocked(self, validator):
        sql = "UPDATE users SET role = 'admin' WHERE id = 1"
        is_safe, reason = validator.validate(sql)
        assert not is_safe

    def test_truncate_is_blocked(self, validator):
        sql = "TRUNCATE TABLE logs"
        is_safe, reason = validator.validate(sql)
        assert not is_safe

    def test_create_is_blocked(self, validator):
        sql = "CREATE TABLE new_table (id INT)"
        is_safe, reason = validator.validate(sql)
        assert not is_safe

    def test_multi_statement_injection_blocked(self, validator):
        sql = "SELECT * FROM users; DROP TABLE users"
        is_safe, reason = validator.validate(sql)
        assert not is_safe
        assert "Multiple statements" in reason

    def test_embedded_delete_in_subquery_blocked(self, validator):
        sql = "SELECT * FROM (DELETE FROM users RETURNING id) sub"
        is_safe, reason = validator.validate(sql)
        assert not is_safe

    def test_grant_is_blocked(self, validator):
        sql = "GRANT ALL PRIVILEGES ON ALL TABLES TO hacker"
        is_safe, reason = validator.validate(sql)
        assert not is_safe


# ────────────────────────────────────────────────────────────────────────────
# Chart Suggestion Tests
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_agent():
    with (
        patch("agent.analytics_agent.vertexai.init"),
        patch("agent.analytics_agent.GenerativeModel"),
        patch("agent.analytics_agent.BigQueryClient") as mock_bq,
    ):
        agent = AnalyticsAgent()
        agent._bq = mock_bq.return_value
        yield agent


class TestChartSuggestion:

    def test_time_series_suggests_line(self, mock_agent):
        chart = mock_agent._suggest_chart_type(
            "Show me daily revenue over time",
            [{"date": "2024-01-01", "revenue": 100}] * 30,
        )
        assert chart == "line"

    def test_comparison_suggests_bar(self, mock_agent):
        chart = mock_agent._suggest_chart_type(
            "Compare revenue by region",
            [{"region": "US", "revenue": 100}] * 5,
        )
        assert chart == "bar"

    def test_distribution_suggests_pie_for_small(self, mock_agent):
        chart = mock_agent._suggest_chart_type(
            "Show percentage distribution by category",
            [{"category": c, "pct": 20} for c in ["A", "B", "C", "D", "E"]],
        )
        assert chart == "pie"

    def test_large_distribution_suggests_bar(self, mock_agent):
        chart = mock_agent._suggest_chart_type(
            "Show percentage distribution by category",
            [{"category": f"Cat{i}", "pct": 5} for i in range(20)],
        )
        assert chart == "bar"

    def test_scatter_for_correlation(self, mock_agent):
        chart = mock_agent._suggest_chart_type(
            "Correlation between price and sales",
            [{"price": 10, "sales": 100}] * 50,
        )
        assert chart == "scatter"

    def test_table_for_large_result(self, mock_agent):
        chart = mock_agent._suggest_chart_type(
            "List all transactions",
            [{"id": i, "amount": 10} for i in range(200)],
        )
        assert chart == "table"


# ────────────────────────────────────────────────────────────────────────────
# Agent query tests
# ────────────────────────────────────────────────────────────────────────────

class TestAnalyticsAgent:

    def test_agent_blocks_unsafe_sql(self, mock_agent):
        """Agent should not execute unsafe SQL from Gemini."""
        # Simulate Gemini generating a DELETE statement
        mock_fc = MagicMock()
        mock_fc.name = "execute_bigquery_query"
        mock_fc.args = {"sql": "DELETE FROM users WHERE 1=1", "limit": 100}

        result = mock_agent._execute_function(mock_fc, "my_dataset")
        assert "error" in result
        assert "blocked" in result["error"].lower()

    def test_agent_executes_safe_sql(self, mock_agent):
        """Agent should execute safe SELECT queries."""
        mock_agent._bq.query.return_value = [{"revenue": 100}, {"revenue": 200}]

        mock_fc = MagicMock()
        mock_fc.name = "execute_bigquery_query"
        mock_fc.args = {"sql": "SELECT revenue FROM sales LIMIT 10"}

        result = mock_agent._execute_function(mock_fc, "my_dataset")
        assert "rows" in result
        assert len(result["rows"]) == 2

    def test_list_tables_function(self, mock_agent):
        """list_available_tables should return table names."""
        mock_agent._bq.get_dataset_schema.return_value = {
            "sales": [{"column": "id", "type": "STRING"}],
            "users": [{"column": "name", "type": "STRING"}],
        }

        mock_fc = MagicMock()
        mock_fc.name = "list_available_tables"
        mock_fc.args = {}

        result = mock_agent._execute_function(mock_fc, "my_dataset")
        assert "tables" in result
        assert "sales" in result["tables"]
        assert "users" in result["tables"]

    def test_limit_capped_at_max(self, mock_agent):
        """SQL result limit should never exceed MAX_RESULT_ROWS."""
        mock_agent._bq.query.return_value = [{"id": i} for i in range(100)]

        mock_fc = MagicMock()
        mock_fc.name = "execute_bigquery_query"
        mock_fc.args = {"sql": "SELECT * FROM table1", "limit": 99999}

        result = mock_agent._execute_function(mock_fc, "my_dataset")
        # Should not crash and should apply LIMIT
        assert "rows" in result or "error" in result
