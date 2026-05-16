"""
EnterpriseIQ ML — Analytics Agent (NL-to-SQL)
Month 5 deliverable.

Implements Gemini Function Calling agentic loop:
  1. User asks natural language question
  2. Gemini generates SQL via function calling
  3. SQL executed safely in BigQuery (SELECT-only whitelist)
  4. Gemini interprets results + suggests chart type
  5. Returns structured AgentResult

Multi-turn conversation supported via session history.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import structlog
import vertexai
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)

from shared.bigquery_client import BigQueryClient
from shared.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

ChartType = Literal["bar", "line", "pie", "table", "scatter", "area"]

# Session history store (in-memory; production uses Firestore)
_agent_sessions: dict[str, list[dict]] = {}


@dataclass
class AgentResult:
    question: str
    sql_generated: str
    results: list[dict]
    chart_suggestion: ChartType
    explanation: str
    row_count: int
    dataset_id: str
    session_id: str | None = None
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SQLSafetyValidator:
    """
    Validates that AI-generated SQL is safe to execute.
    Only SELECT statements are allowed — no DDL/DML.
    """

    FORBIDDEN_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
        "TRUNCATE", "MERGE", "REPLACE", "GRANT", "REVOKE",
        "EXEC", "EXECUTE", "CALL", "LOAD", "COPY",
    }

    def validate(self, sql: str) -> tuple[bool, str]:
        """Returns (is_safe, reason). Reason is empty string if safe."""
        clean = sql.strip().upper()

        # Must start with SELECT or WITH (for CTEs)
        if not (clean.startswith("SELECT") or clean.startswith("WITH")):
            return False, "Only SELECT queries are allowed"

        # Check for semicolon injection
        # Allow trailing semicolon only
        clean_stripped = clean.rstrip(";").strip()
        if ";" in clean_stripped:
            return False, "Multiple statements detected"

        # Check for forbidden keywords (word boundary match)
        for kw in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{kw}\b", clean):
                return False, f"Forbidden keyword detected: {kw}"

        # Check for comment-based injection
        if "--" in sql and "/*" in sql:
            return False, "Suspicious comment pattern"

        return True, ""


class AnalyticsAgent:
    """
    Gemini Function Calling agent for natural language BigQuery analytics.
    Developer B Month 5.
    """

    MAX_TURNS = 5
    MAX_RESULT_ROWS = 1000

    def __init__(self) -> None:
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)
        self._gemini = GenerativeModel(settings.gemini_pro_model)
        self._bq = BigQueryClient()
        self._validator = SQLSafetyValidator()

        # Define tools for Gemini function calling
        self._tool = Tool(
            function_declarations=[
                FunctionDeclaration(
                    name="execute_bigquery_query",
                    description=(
                        "Execute a SQL SELECT query on BigQuery and return the results. "
                        "ONLY use SELECT statements. Never INSERT, UPDATE, DELETE, or DROP."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "The BigQuery SQL query to execute",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of rows to return (default 100)",
                            },
                        },
                        "required": ["sql"],
                    },
                ),
                FunctionDeclaration(
                    name="get_table_schema",
                    description="Get the column schema of a specific BigQuery table",
                    parameters={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table",
                            }
                        },
                        "required": ["table_name"],
                    },
                ),
                FunctionDeclaration(
                    name="list_available_tables",
                    description="List all tables available for querying in the dataset",
                    parameters={"type": "object", "properties": {}},
                ),
            ]
        )

        logger.info("AnalyticsAgent initialised")

    # ── Function Execution ────────────────────────────────────────────────────

    def _execute_function(self, function_call: Any,
                           dataset_id: str) -> dict[str, Any]:
        """Execute a Gemini function call and return structured result."""
        name = function_call.name
        args = dict(function_call.args)

        if name == "execute_bigquery_query":
            sql = args.get("sql", "")
            limit = min(int(args.get("limit", 100)), self.MAX_RESULT_ROWS)

            # Safety check
            is_safe, reason = self._validator.validate(sql)
            if not is_safe:
                return {"error": f"SQL blocked by safety validator: {reason}", "rows": []}

            # Add LIMIT if not present
            if "LIMIT" not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT {limit}"

            try:
                rows = self._bq.query(sql)
                return {"rows": rows[:limit], "row_count": len(rows), "sql": sql}
            except Exception as e:
                return {"error": str(e), "rows": []}

        elif name == "get_table_schema":
            table_name = args.get("table_name", "")
            try:
                schema = self._bq.get_dataset_schema(dataset_id)
                return {"schema": schema.get(table_name, {}), "table": table_name}
            except Exception as e:
                return {"error": str(e)}

        elif name == "list_available_tables":
            try:
                schema = self._bq.get_dataset_schema(dataset_id)
                return {"tables": list(schema.keys())}
            except Exception as e:
                return {"error": str(e)}

        return {"error": f"Unknown function: {name}"}

    # ── Chart Suggestion ──────────────────────────────────────────────────────

    def _suggest_chart_type(self, question: str, results: list[dict]) -> ChartType:
        """Heuristic chart type suggestion based on question and result shape."""
        q = question.lower()
        cols = list(results[0].keys()) if results else []
        col_count = len(cols)
        row_count = len(results)

        if any(kw in q for kw in ["trend", "over time", "daily", "monthly", "weekly", "per day"]):
            return "line"
        if any(kw in q for kw in ["compare", "by region", "by product", "top", "rank"]):
            return "bar"
        if any(kw in q for kw in ["distribution", "share", "percentage", "proportion"]):
            return "pie" if row_count <= 6 else "bar"
        if any(kw in q for kw in ["correlation", "vs", "scatter", "relationship"]):
            return "scatter"
        if col_count == 1 or row_count > 50:
            return "table"
        if col_count >= 2 and any(isinstance(v, (int, float))
                                   for row in results[:3] for v in row.values()):
            return "bar"
        return "table"

    # ── Main Agent Loop ───────────────────────────────────────────────────────

    def query(self, question: str, dataset_id: str,
              session_id: str | None = None) -> AgentResult:
        """
        Multi-turn Gemini agentic loop.
        Called by Person A's backend via /internal/agent/nl2sql.
        """
        logger.info("Agent query started", dataset_id=dataset_id, session_id=session_id)

        schema = self._bq.get_dataset_schema(dataset_id)
        schema_text = json.dumps(schema, indent=2)

        # Build session context
        history_text = ""
        if session_id and session_id in _agent_sessions:
            prev = _agent_sessions[session_id][-4:]  # last 2 turns
            history_text = "\n".join(
                [f"{m['role'].upper()}: {m['content']}" for m in prev]
            )
            history_text = f"\nPrevious conversation:\n{history_text}\n"

        system_instruction = f"""You are an expert BigQuery data analyst for an enterprise platform.
You have access to the following dataset schema:
{schema_text}
{history_text}
When answering questions:
1. Use execute_bigquery_query to run SQL (SELECT only)
2. After getting results, provide a clear business interpretation
3. Always be specific about the numbers and what they mean
4. Use get_table_schema if you need column details
5. NEVER generate INSERT, UPDATE, DELETE, DROP, or any write operations"""

        chat = self._gemini.start_chat()

        last_results: list[dict] = []
        last_sql: str = ""
        final_text: str = ""

        # Agentic loop
        for turn in range(self.MAX_TURNS):
            message = question if turn == 0 else "Please continue with the analysis."

            if turn == 0:
                # Inject system instruction in first turn
                full_message = f"{system_instruction}\n\nUser Question: {question}"
            else:
                full_message = message

            response = chat.send_message(
                full_message,
                tools=[self._tool],
                generation_config=GenerationConfig(temperature=0.1),
            )

            candidate = response.candidates[0]
            has_function_call = False

            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    has_function_call = True
                    fc_result = self._execute_function(part.function_call, dataset_id)

                    if "rows" in fc_result and fc_result["rows"]:
                        last_results = fc_result["rows"]
                    if "sql" in fc_result:
                        last_sql = fc_result["sql"]

                    # Send function result back to model
                    chat.send_message(
                        Part.from_function_response(
                            name=part.function_call.name,
                            response={"result": fc_result},
                        ),
                        tools=[self._tool],
                    )

            if not has_function_call:
                # Model finished — extract final text
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text += part.text
                break

        if not final_text:
            final_text = "Analysis complete. Please review the query results."

        chart_type = self._suggest_chart_type(question, last_results)

        # Save session
        if session_id:
            _agent_sessions.setdefault(session_id, [])
            _agent_sessions[session_id].append({"role": "user", "content": question})
            _agent_sessions[session_id].append({"role": "assistant", "content": final_text})

        result = AgentResult(
            question=question,
            sql_generated=last_sql,
            results=last_results,
            chart_suggestion=chart_type,
            explanation=final_text,
            row_count=len(last_results),
            dataset_id=dataset_id,
            session_id=session_id,
        )

        logger.info("Agent query complete",
                    sql_len=len(last_sql), result_rows=len(last_results))
        return result
