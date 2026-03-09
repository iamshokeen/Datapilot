"""
DataPilot Phase 2 — Agent State
Shared TypedDict that flows through every LangGraph node.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    connection_id: str              # database connection ID
    original_question: str          # raw user question

    # ── Query Planner ──────────────────────────────────────────────────────
    sub_questions: list[str]        # decomposed sub-questions (≥1)
    current_sub_q_index: int        # which sub-question we're processing

    # ── SQL Generator ──────────────────────────────────────────────────────
    sql_query: str                  # generated SQL for current sub-question
    sql_error: Optional[str]        # last SQL execution error (if any)
    retry_count: int                # number of SQL rewrite retries so far

    # ── SQL Executor ───────────────────────────────────────────────────────
    query_result: list[dict]        # rows returned by the DB
    execution_success: bool         # True = query ran OK

    # ── Python Analyst ─────────────────────────────────────────────────────
    analysis_result: Optional[dict] # enriched stats / aggregations

    # ── Sub-question accumulator ───────────────────────────────────────────
    all_results: list[dict]         # results for every sub-question

    # ── Insight Narrator ───────────────────────────────────────────────────
    narrative: str                  # natural-language summary

    # ── Chart Suggester ────────────────────────────────────────────────────
    chart_suggestion: dict          # {type, x_axis, y_axis, reason}

    # ── Final response ─────────────────────────────────────────────────────
    final_response: dict            # assembled API response payload
    error: Optional[str]            # top-level error message

