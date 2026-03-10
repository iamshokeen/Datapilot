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

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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


def insight_narrator(state: AgentState) -> AgentState:
    original_q = state.get("original_question", "")
    all_results: list[dict] = state.get("all_results", [])

    if not all_results:
        return {**state, "narrative": "No data was returned for this query."}

    # Build a compact summary for Claude
    results_summary = []
    for item in all_results:
        analysis = item.get("analysis") or {}  # Handle None case
        results_summary.append(
            {
                "sub_question": item.get("sub_question"),
                "row_count": analysis.get("row_count", 0),
                "stats": analysis.get("stats", {}),
                "sample_rows": _truncate_rows(analysis.get("rows", []), 15),
            }
        )

    prompt = f"""Original question: {original_q}

Results:
{json.dumps(results_summary, indent=2, default=str)}

Please write the narrative summary."""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        narrative = response.content[0].text.strip()
        logger.info("[insight_narrator] Narrative generated (%d chars)", len(narrative))
        return {**state, "narrative": narrative}
    except Exception as exc:
        logger.error("[insight_narrator] Failed: %s", exc)
        return {
            **state,
            "narrative": f"Analysis complete. {len(all_results)} sub-question(s) processed with {sum(((r or {}).get('analysis') or {}).get('row_count', 0) for r in all_results)} total rows returned.",
        }

