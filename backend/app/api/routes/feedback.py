"""
POST /agent/feedback — thumbs up/down on a query result.
Thumbs up → verified=True → ECHO eligible + triggers LORE update.
Thumbs down → saves correction_note so ECHO can learn from the failure next time.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import psycopg2

from app.config import settings
from app.core.lore import update_lore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., description="Session ID of the conversation")
    turn_number: int = Field(..., description="Turn number within the session (0-indexed)")
    verdict: str = Field(..., pattern="^(up|down)$", description="'up' or 'down'")
    correction_note: Optional[str] = Field(None, description="For thumbs down: what the user expected instead")


class FeedbackResponse(BaseModel):
    ok: bool
    verified: bool
    lore_updated: bool = False


def _get_conn():
    return psycopg2.connect(
        host=settings.datapilot_db_host,
        port=settings.datapilot_db_port,
        dbname=settings.datapilot_db_name,
        user=settings.datapilot_db_user,
        password=settings.datapilot_db_password,
    )


@router.post("/feedback", response_model=FeedbackResponse, summary="Submit thumbs up/down on a query result")
async def submit_feedback(request: FeedbackRequest):
    verified = request.verdict == "up"
    lore_updated = False

    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                if verified:
                    # Thumbs up: mark as verified, clear any previous correction
                    cur.execute(
                        """
                        UPDATE query_history qh
                        SET verified = TRUE, feedback = 'up', correction_note = NULL
                        FROM conversation_turns ct
                        WHERE ct.session_id = %s
                          AND ct.turn_number = %s
                          AND qh.session_id = ct.session_id
                          AND qh.question = ct.question
                        RETURNING qh.id, qh.question, qh.generated_sql
                        """,
                        (request.session_id, request.turn_number),
                    )
                else:
                    # Thumbs down: save correction note — keep verified=NULL (not blacklisted)
                    # so ECHO can still find it and apply the correction via Tier 2
                    cur.execute(
                        """
                        UPDATE query_history qh
                        SET verified = NULL, feedback = 'down', correction_note = %s
                        FROM conversation_turns ct
                        WHERE ct.session_id = %s
                          AND ct.turn_number = %s
                          AND qh.session_id = ct.session_id
                          AND qh.question = ct.question
                        RETURNING qh.id, qh.question, qh.generated_sql
                        """,
                        (request.correction_note, request.session_id, request.turn_number),
                    )
                row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Turn not found in query history")

        _, question, sql = row

        # If thumbs up and we have SQL, trigger LORE update
        if verified and sql:
            try:
                update_lore(question=question, sql=sql)
                lore_updated = True
            except Exception as exc:
                logger.warning("[feedback] LORE update failed: %s", exc)

        logger.info(
            "[feedback] session=%s turn=%d verdict=%s correction=%s lore_updated=%s",
            request.session_id, request.turn_number, request.verdict,
            bool(request.correction_note), lore_updated,
        )
        return FeedbackResponse(ok=True, verified=verified, lore_updated=lore_updated)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[feedback] Failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
