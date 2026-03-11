"""
DataPilot — Conversation History Service
Provides sync helpers (psycopg2) for storing and retrieving multi-turn
conversation context. Agent nodes are sync, so we use psycopg2 directly.
"""
import json
import logging
from typing import Optional

import psycopg2
import psycopg2.extras

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_DATA_ROWS = 1000
_HISTORY_TURNS = 3  # how many previous turns to inject as context


def _get_conn():
    return psycopg2.connect(
        host=settings.datapilot_db_host,
        port=settings.datapilot_db_port,
        dbname=settings.datapilot_db_name,
        user=settings.datapilot_db_user,
        password=settings.datapilot_db_password,
    )


def get_history(session_id: str) -> list[dict]:
    """
    Return last _HISTORY_TURNS turns for a session, oldest-first.
    Each entry: {question, summary, data (list[dict] | None)}
    """
    if not session_id:
        return []
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT question, summary, data
                    FROM conversation_turns
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (session_id, _HISTORY_TURNS),
                )
                rows = cur.fetchall()
        conn.close()
        # Reverse so oldest is first (chronological order for context)
        history = list(reversed([dict(r) for r in rows]))
        logger.info("[conversation] Loaded %d history turns for session %s", len(history), session_id)
        return history
    except Exception as exc:
        logger.warning("[conversation] Failed to load history: %s", exc)
        return []


def save_turn(
    session_id: str,
    connection_id: str,
    question: str,
    narrative: Optional[str],
    data: Optional[list[dict]],
) -> None:
    """
    Save a completed turn. Caps data at _MAX_DATA_ROWS rows.
    Summary is the first 200 chars of the narrative (no extra LLM call).
    """
    if not session_id:
        return
    try:
        # Cap rows
        capped_data = (data or [])[:_MAX_DATA_ROWS]

        # Summary = first sentence of narrative, max 200 chars
        summary = ""
        if narrative:
            first_sentence = narrative.split(".")[0].strip()
            summary = first_sentence[:200]

        # Get next turn_number
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(turn_number), -1) + 1 FROM conversation_turns WHERE session_id = %s",
                    (session_id,),
                )
                turn_number = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO conversation_turns
                        (session_id, connection_id, turn_number, question, narrative, summary, data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session_id,
                        connection_id,
                        turn_number,
                        question,
                        narrative,
                        summary,
                        json.dumps(capped_data) if capped_data else None,
                    ),
                )
        conn.close()
        logger.info("[conversation] Saved turn %d for session %s", turn_number, session_id)
    except Exception as exc:
        logger.warning("[conversation] Failed to save turn: %s", exc)
