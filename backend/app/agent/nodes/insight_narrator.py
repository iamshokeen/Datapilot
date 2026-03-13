"""
Node 6 — insight_narrator
Generates a concise, executive-level natural-language summary of all
sub-question results using Claude.
"""
import json
import logging
import os

import anthropic

from app.agent.state import AgentState
from app.config import settings, system_block

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_SYSTEM = """You are an expert data analyst and storyteller for Lohono Stays, a luxury villa rental company with 139+ properties across India.

You will receive:
- The original user question
- One or more sub-questions with their data results and statistics

Your task: Write a concise, insightful narrative (3-6 sentences) that:
1. Directly answers the original question
2. Highlights the most important numbers/trends
3. Calls out any surprises or notable patterns
4. Uses business-friendly language (avoid SQL jargon)
5. Mentions property names, revenue figures, or booking counts when relevant

Tone: Confident, data-driven, executive summary style. No bullet points — flowing prose only.
"""


def _truncate_rows(rows: list[dict], max_rows: int = 20) -> list[dict]:
    return rows[:max_rows]


def _sanitize(obj):
    """Recursively convert numpy/Decimal/datetime types to native Python for JSON."""
    import decimal, datetime
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def insight_narrator(state: AgentState) -> AgentState:
    original_q = state.get("original_question", "")
    all_results: list[dict] = state.get("all_results", [])

    if not all_results:
        return {**state, "narrative": "No data was returned for this query."}

    # Check if all sub-queries failed execution
    all_failed = all(not item.get("execution_success", False) for item in all_results)
    if all_failed:
        first_error = next((item.get("error") for item in all_results if item.get("error")), None)
        error_detail = f" Error: {first_error}" if first_error else ""
        return {
            **state,
            "narrative": f"The query could not be executed after multiple attempts.{error_detail} Try rephrasing your question or check that the relevant data exists.",
        }

    # Check if queries succeeded but returned 0 rows
    total_rows = sum((item.get("analysis") or {}).get("row_count", 0) for item in all_results)
    if total_rows == 0:
        return {
            **state,
            "narrative": "The query executed successfully but returned no results. The filters or date range may not match any data — try adjusting them.",
        }

    # Build a compact summary for Claude — sanitize all values first
    results_summary = []
    for item in all_results:
        analysis = item.get("analysis") or {}
        results_summary.append(
            {
                "sub_question": item.get("sub_question"),
                "row_count": analysis.get("row_count", 0),
                "stats": _sanitize(analysis.get("stats", {})),
                "sample_rows": _sanitize(_truncate_rows(analysis.get("rows", []), 15)),
            }
        )

    def _default(obj):
        """Fallback JSON encoder for any remaining non-serializable types."""
        return str(obj)

    prompt = f"""Original question: {original_q}

Results:
{json.dumps(results_summary, indent=2, default=_default)}

Please write the narrative summary."""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            system=[system_block(_SYSTEM)],
            messages=[{"role": "user", "content": prompt}],
        )
        node_usage = {
            "input": getattr(response.usage, "input_tokens", 0) or 0,
            "output": getattr(response.usage, "output_tokens", 0) or 0,
            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        }
        token_tracker = dict(state.get("token_tracker") or {})
        token_tracker["insight_narrator"] = node_usage

        narrative = response.content[0].text.strip()
        logger.info("[insight_narrator] Narrative generated (%d chars)", len(narrative))
        return {**state, "narrative": narrative, "token_tracker": token_tracker}
    except Exception as exc:
        import traceback
        logger.error("[insight_narrator] Failed: %s\n%s", exc, traceback.format_exc())
        return {
            **state,
            "narrative": f"Data retrieved successfully ({total_rows} rows) but the narrative summary could not be generated. Please check the table below for results.",
        }

