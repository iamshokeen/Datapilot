"""
Node — echo_lookup
Runs ECHO semantic search before SQL generation.
Sets echo_tier in state to route the graph.
"""
import logging

from app.agent.state import AgentState
from app.core.echo import find_similar

logger = logging.getLogger(__name__)


def echo_lookup(state: AgentState) -> AgentState:
    sub_questions = state.get("sub_questions", [])
    idx = state.get("current_sub_q_index", 0)
    question = sub_questions[idx] if idx < len(sub_questions) else state.get("original_question", "")
    connection_id = state.get("connection_id", "")

    result = find_similar(question, connection_id)

    if result is None:
        logger.info("[echo_lookup] No match — Tier 3 (full generation)")
        return {**state, "echo_tier": 3, "echo_cached_sql": None, "echo_cached_question": None}

    return {
        **state,
        "echo_tier": result["tier"],
        "echo_cached_sql": result["cached_sql"],
        "echo_cached_question": result.get("cached_question"),
        "echo_similarity": result["similarity"],
        "echo_history_id": result["history_id"],
        # For Tier 1: pre-load the cached SQL directly
        "sql_query": result["cached_sql"] if result["tier"] == 1 else state.get("sql_query", ""),
        "execution_success": False,
        "sql_error": None,
    }
