"""
Node — sql_modifier (ECHO Tier 2)
Given a cached SQL and a new question that differs in parameters (date/location/limit),
asks Claude to minimally modify the SQL to match the new question.
Much cheaper than full SQL generation.
"""
import logging
import os

import anthropic

from app.agent.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_SYSTEM = """You are a SQL modification assistant for a PostgreSQL analytics database.

You will receive:
- A verified, working SQL query that answered a similar question
- The new question that needs answering
- What changed between the two questions

Your task: Minimally modify the cached SQL to answer the new question.
- Change ONLY what needs to change (dates, locations, filters, limits, groupings)
- Keep all table names, joins, and business logic identical
- Return ONLY the modified SQL — no explanation, no markdown fences

If the modification is not possible with minimal changes, return the original SQL unchanged."""


def sql_modifier(state: AgentState) -> AgentState:
    cached_sql = state.get("echo_cached_sql", "")
    cached_question = state.get("echo_cached_question", "")
    sub_questions = state.get("sub_questions", [])
    idx = state.get("current_sub_q_index", 0)
    new_question = sub_questions[idx] if idx < len(sub_questions) else state.get("original_question", "")

    if not cached_sql:
        logger.warning("[sql_modifier] No cached SQL — falling through to generator")
        return {**state, "echo_tier": 3}

    correction_note = state.get("echo_correction_note")
    logger.info("[sql_modifier] Modifying cached SQL for: %s (correction=%s)", new_question[:60], bool(correction_note))

    correction_block = ""
    if correction_note:
        correction_block = f"""
IMPORTANT — A previous attempt at this question was marked incorrect by the user.
User feedback: "{correction_note}"
You MUST ensure the modified SQL addresses this issue.
"""

    prompt = f"""Cached question: {cached_question}

New question: {new_question}
{correction_block}
Cached SQL:
{cached_sql}

Modify the SQL minimally to answer the new question."""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        modified_sql = response.content[0].text.strip()
        # Strip markdown fences if present
        if modified_sql.startswith("```"):
            lines = modified_sql.split("\n")
            modified_sql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        logger.info("[sql_modifier] Modified SQL ready")
        return {
            **state,
            "sql_query": modified_sql,
            "sql_error": None,
            "execution_success": False,
        }
    except Exception as exc:
        logger.error("[sql_modifier] Failed: %s", exc)
        # Fall through to full sql_generator
        return {**state, "echo_tier": 3, "sql_query": "", "sql_error": None}
