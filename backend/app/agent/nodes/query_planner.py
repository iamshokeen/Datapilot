"""
Node 1 — query_planner
Breaks a complex / multi-part user question into ordered sub-questions.
When conversation history is present, also classifies whether the question
needs new SQL or can be answered from the previous turn's data.
"""
import json
import logging
import os

import anthropic

from app.agent.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_SYSTEM = """You are a query planning assistant for a luxury villa rental analytics platform called Lohono Stays.

Your job:
1. Classify whether the question needs a NEW database query or can be answered from previously fetched data.
2. If a new query is needed, decompose it into the minimum number of atomic sub-questions each answerable by a single SQL query.

Classification rules (requires_new_query):
- Set false ONLY when the question is clearly about data already returned in the conversation history
  (e.g. "which of those had the highest revenue?", "average those numbers", "explain why that happened", "sort by X", "top 5 from those results")
- Set true for any question that needs fresh data from the database, new filters, different time ranges, different metrics, or new tables.
- When in doubt, set true.

Decomposition rules (sub_questions):
- If requires_new_query is false: return a single sub-question restating what the user wants from the previous data.
- If requires_new_query is true and the question is simple: return exactly ONE sub-question.
- If requires_new_query is true and multi-part: split into up to 4 sub-questions, each answerable by one SQL query.
- Each sub-question must be answerable via SQL against a relational DB.

Return ONLY valid JSON — no markdown, no explanation.

Output format:
{"requires_new_query": true|false, "sub_questions": ["sub-question 1", ...]}
"""


def _build_history_context(history: list[dict]) -> str:
    """Build a compact context string from conversation history."""
    if not history:
        return ""
    lines = ["Previous conversation turns (oldest first):"]
    for i, turn in enumerate(history, 1):
        summary = turn.get("summary") or "(no summary)"
        question = turn.get("question", "")
        lines.append(f"  Turn {i}: Q: {question!r} → {summary}")
    return "\n".join(lines)


def query_planner(state: AgentState) -> AgentState:
    question = state.get("original_question", "")
    history: list[dict] = state.get("conversation_history", [])
    logger.info("[query_planner] Planning: %s | history turns: %d", question, len(history))

    history_ctx = _build_history_context(history)
    user_content = question
    if history_ctx:
        user_content = f"{history_ctx}\n\nCurrent question: {question}"

    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    try:
        response = _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_content}],
        )
        usage = {
            "input": getattr(response.usage, "input_tokens", 0) or 0,
            "output": getattr(response.usage, "output_tokens", 0) or 0,
            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        }
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        sub_questions = parsed.get("sub_questions", [question])
        requires_new_query = parsed.get("requires_new_query", True)
    except Exception as exc:
        logger.warning("[query_planner] Falling back to original question: %s", exc)
        sub_questions = [question]
        requires_new_query = True

    logger.info(
        "[query_planner] requires_new_query=%s sub_questions=%s",
        requires_new_query, sub_questions
    )

    # If re-using previous data, inject it as query_result from last turn
    reuse_query_result: list[dict] = []
    if not requires_new_query and history:
        last_data = history[-1].get("data") or []
        reuse_query_result = last_data
        logger.info("[query_planner] Re-using %d rows from last turn", len(reuse_query_result))

    token_tracker = dict(state.get("token_tracker") or {})
    token_tracker["query_planner"] = usage

    return {
        **state,
        "sub_questions": sub_questions,
        "current_sub_q_index": 0,
        "all_results": [],
        "retry_count": 0,
        "requires_new_query": requires_new_query,
        "query_result": reuse_query_result if not requires_new_query else state.get("query_result", []),
        "execution_success": True if not requires_new_query else False,
        "sql_query": "" if not requires_new_query else state.get("sql_query", ""),
        "sql_error": None,
        "token_tracker": token_tracker,
    }
