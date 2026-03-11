"""
DataPilot Phase 2 — Agent State
Shared TypedDict that flows through every LangGraph node.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    connection_id: str
    original_question: str
    session_id: Optional[str]

    # ── Conversation history (multi-turn) ──────────────────────────────────
    conversation_history: list[dict]

    # ── Query Planner ──────────────────────────────────────────────────────
    sub_questions: list[str]
    current_sub_q_index: int
    requires_new_query: bool

    # ── ECHO (semantic SQL cache) ──────────────────────────────────────────
    echo_tier: Optional[int]          # 1=exact, 2=modify, 3=full, None=not checked
    echo_cached_sql: Optional[str]    # cached SQL from ECHO lookup
    echo_cached_question: Optional[str]  # the original cached question
    echo_similarity: Optional[float]  # cosine similarity score
    echo_history_id: Optional[int]    # query_history.id of the matched row

    # ── SQL Generator ──────────────────────────────────────────────────────
    sql_query: str
    sql_error: Optional[str]
    retry_count: int

    # ── SQL Executor ───────────────────────────────────────────────────────
    query_result: list[dict]
    execution_success: bool

    # ── Python Analyst ─────────────────────────────────────────────────────
    analysis_result: Optional[dict]

    # ── Sub-question accumulator ───────────────────────────────────────────
    all_results: list[dict]

    # ── Insight Narrator ───────────────────────────────────────────────────
    narrative: str

    # ── Chart Suggester ────────────────────────────────────────────────────
    chart_suggestion: dict

    # ── Final response ─────────────────────────────────────────────────────
    final_response: dict
    error: Optional[str]
