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
"""


def sql_rewriter(state: AgentState) -> AgentState:
    sub_questions: list[str] = state.get("sub_questions", [])
    idx: int = state.get("current_sub_q_index", 0)
    question = sub_questions[idx] if idx < len(sub_questions) else state.get("original_question", "")

    broken_sql = state.get("sql_query", "")
    error_msg = state.get("sql_error", "Unknown error")
    retry_count = state.get("retry_count", 0)

    logger.info("[sql_rewriter] Retry %d for question: %s", retry_count + 1, question)

    prompt = f"""User question: {question}

Failed SQL:
{broken_sql}

PostgreSQL error:
{error_msg}

Please provide a corrected SQL query."""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=_SYSTEM,
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
            "sql_error": None,          # clear error so executor can retry
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

