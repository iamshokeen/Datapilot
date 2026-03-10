"""
Helper nodes:
- accumulate_result  : saves current sub-question result and advances the index
- assemble_response  : builds the final API response payload
"""
import logging

from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def accumulate_result(state: AgentState) -> AgentState:
    """Save current sub-question result and advance index."""
    sub_questions: list[str] = state.get("sub_questions", [])
    idx: int = state.get("current_sub_q_index", 0)
    all_results: list[dict] = list(state.get("all_results", []))

    current_q = sub_questions[idx] if idx < len(sub_questions) else state.get("original_question", "")

    all_results.append(
        {
            "sub_question": current_q,
            "sql": state.get("sql_query", ""),
            "analysis": state.get("analysis_result", {}),
            "execution_success": state.get("execution_success", False),
            "retries": state.get("retry_count", 0),
        }
    )

    logger.info(
        "[accumulate_result] Saved result for sub-q %d/%d", idx + 1, len(sub_questions)
    )

    return {
        **state,
        "all_results": all_results,
        "current_sub_q_index": idx + 1,
        # Reset per-sub-question state for next iteration
        "sql_query": "",
        "sql_error": None,
        "retry_count": 0,
        "query_result": [],
        "analysis_result": None,
        "execution_success": False,
    }


def _jsonify_value(v):
    """Convert non-JSON-serializable types to JSON-compatible ones."""
    from decimal import Decimal
    if isinstance(v, Decimal):
        return float(v)
    return v


def _jsonify_dict(d: dict) -> dict:
    """Recursively convert dict values to JSON-serializable types."""
    return {k: _jsonify_value(v) for k, v in d.items()}


def assemble_response(state: AgentState) -> AgentState:
    """Build the final JSON-serialisable response payload."""
    all_results: list[dict] = state.get("all_results", [])

    # Merge rows from all sub-questions for the primary data field
    combined_rows: list[dict] = []
    for r in all_results:
        rows = (r.get("analysis") or {}).get("rows", [])
        # Convert Decimal and other non-JSON types
        combined_rows.extend([_jsonify_dict(row) for row in rows])

    final_response = {
        "question": state.get("original_question", ""),
        "sub_questions": state.get("sub_questions", []),
        "results": all_results,
        "data": combined_rows,
        "narrative": state.get("narrative", ""),
        "chart_suggestion": state.get("chart_suggestion", {}),
        "total_rows": len(combined_rows),
        "sub_question_count": len(all_results),
    }

    logger.info(
        "[assemble_response] Final response assembled — %d rows, %d sub-questions",
        len(combined_rows),
        len(all_results),
    )

    return {**state, "final_response": final_response}

