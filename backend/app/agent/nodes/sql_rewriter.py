"""
Node 4 — sql_rewriter
If SQL execution failed, sends the error + original SQL back to Claude
to generate a corrected query. Max 2 retries (controlled in graph routing).
"""
import logging
import os
import re

import anthropic

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SYSTEM = """You are an expert PostgreSQL query fixer for the Lohono Stays analytics platform.

You will receive:
1. The original user question
2. The SQL query that was attempted
3. The error message from PostgreSQL

Your task: return a corrected SQL query that fixes the error.

Rules:
- Return ONLY the raw SQL query — no markdown, no explanation, no backticks.
- Preserve the intent of the original query.
- Fix syntax errors, wrong column names, wrong table names, type mismatches.
- If the error suggests a missing table/column, use a reasonable alternative or add a graceful fallback (e.g. COALESCE, CAST).
- ROUND requires NUMERIC: always fix to ROUND(value::NUMERIC, 2) — never ROUND(double_precision, integer).
"""


_SIMPLIFY_SYSTEM = """You are an expert PostgreSQL query writer for the Lohono Stays analytics platform.

The previous attempt to generate SQL for the user's question produced a query that was too long and got cut off.

Your task: write a functionally equivalent but MORE CONCISE SQL query that produces the same result.

Strategies to reduce length:
- Combine multiple CTEs into a single query using subqueries or window functions where possible
- For FY-over-FY comparisons, use conditional aggregation (SUM(CASE WHEN ... THEN ... END)) in one query instead of separate CTEs per year
- Avoid repeating the channel CASE expression — use a subquery or CTE once and reference it
- Remove redundant joins if the needed columns are already available

Rules:
- Return ONLY the raw SQL query — no markdown, no explanation, no backticks
- ONLY SELECT statements
- Must be valid PostgreSQL
"""


def sql_rewriter(state: AgentState) -> AgentState:
    sub_questions: list[str] = state.get("sub_questions", [])
    idx: int = state.get("current_sub_q_index", 0)
    question = sub_questions[idx] if idx < len(sub_questions) else state.get("original_question", "")

    broken_sql = state.get("sql_query", "")
    error_msg = state.get("sql_error", "Unknown error")
    retry_count = state.get("retry_count", 0)

    logger.info("[sql_rewriter] Retry %d for question: %s", retry_count + 1, question)

    # Choose strategy based on error type
    is_truncated = error_msg and "SQL_TRUNCATED" in error_msg

    if is_truncated:
        logger.info("[sql_rewriter] Truncation detected — requesting simplified query")
        system = _SIMPLIFY_SYSTEM
        prompt = f"""User question: {question}

The previous SQL query was too long and got cut off. Truncation reason: {error_msg}

Partial SQL (cut off):
{broken_sql[:500]}...

Please write a simpler, more concise SQL query that answers the same question."""
    else:
        system = _SYSTEM
        prompt = f"""User question: {question}

Failed SQL:
{broken_sql}

PostgreSQL error:
{error_msg}

Please provide a corrected SQL query."""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        fixed_sql = response.content[0].text.strip()
        # Strip any accidental fencing
        fixed_sql = re.sub(r"^```[a-z]*\n?", "", fixed_sql, flags=re.IGNORECASE)
        fixed_sql = re.sub(r"\n?```$", "", fixed_sql)
        fixed_sql = fixed_sql.strip()

        logger.info("[sql_rewriter] Fixed SQL: %s", fixed_sql[:200])
        return {
            **state,
            "sql_query": fixed_sql,
            "sql_error": None,
            "retry_count": retry_count + 1,
            "execution_success": False,
        }
    except Exception as exc:
        logger.error("[sql_rewriter] Rewrite failed: %s", exc)
        return {
            **state,
            "sql_error": f"Rewrite failed: {exc}",
            "retry_count": retry_count + 1,
        }

