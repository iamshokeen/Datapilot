"""
Node 1 — query_planner
Breaks a complex / multi-part user question into ordered sub-questions.
Simple questions pass through as a single-item list.
"""
import json
import logging
import os

import anthropic

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SYSTEM = """You are a query planning assistant for a luxury villa rental analytics platform called Lohono Stays.

Your job: decompose a user's question into the minimum number of atomic sub-questions that can each be answered by a single SQL query.

Rules:
- If the question is simple and self-contained, return exactly ONE sub-question (restate it clearly).
- If the question has multiple distinct parts (e.g. "What are total bookings AND average revenue per property?"), split them.
- Maximum 4 sub-questions.
- Each sub-question must be answerable via SQL against a relational DB.
- Return ONLY valid JSON — no markdown, no explanation.

Output format:
{"sub_questions": ["sub-question 1", "sub-question 2", ...]}
"""


def query_planner(state: AgentState) -> AgentState:
    question = state.get("original_question", "")
    logger.info("[query_planner] Planning: %s", question)

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": question}],
        )
        raw = response.content[0].text.strip()
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        sub_questions = parsed.get("sub_questions", [question])
    except Exception as exc:
        logger.warning("[query_planner] Falling back to original question: %s", exc)
        sub_questions = [question]

    logger.info("[query_planner] Sub-questions: %s", sub_questions)
    return {
        **state,
        "sub_questions": sub_questions,
        "current_sub_q_index": 0,
        "all_results": [],
        "retry_count": 0,
    }

