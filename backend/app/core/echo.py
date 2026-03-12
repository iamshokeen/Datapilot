"""
ECHO — Every Cached Hit Optimizes
Three-tier semantic SQL cache powered by OpenAI embeddings.

Tier 1 (sim >= 0.95, entities match) — exact SQL recycle, skip Claude entirely
Tier 2 (sim 0.82–0.95 OR entities differ) — SQL modifier gets cached SQL + diff
Tier 3 (sim < 0.82) — full Claude pipeline
"""
import logging
import re
from typing import Optional

import psycopg2
import psycopg2.extras

from app.config import settings
from app.core.embedding import EmbeddingClient

logger = logging.getLogger(__name__)

TIER1_THRESHOLD = 0.95
TIER2_THRESHOLD = 0.82

_embedder = None


def _get_embedder() -> EmbeddingClient:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingClient()
    return _embedder


def _get_conn():
    return psycopg2.connect(
        host=settings.datapilot_db_host,
        port=settings.datapilot_db_port,
        dbname=settings.datapilot_db_name,
        user=settings.datapilot_db_user,
        password=settings.datapilot_db_password,
    )


# ── Entity extraction ─────────────────────────────────────────────────────────

_TEMPORAL = re.compile(
    r'\b(\d+)\s*(month|year|week|day)s?\b'
    r'|\blast\s+(month|year|week|quarter|year)\b'
    r'|\bthis\s+(month|year|week|quarter)\b'
    r'|\bQ[1-4]\s*\d{0,4}\b'
    r'|\b(january|february|march|april|may|june|july|august'
    r'|september|october|november|december)\b'
    r'|\b(20\d{2})\b',
    re.IGNORECASE,
)

_LIMIT = re.compile(r'\b(top|bottom|first|last)\s+(\d+)\b', re.IGNORECASE)

_METRIC = re.compile(
    r'\b(revenue|gmv|bookings?|occupancy|rating|cancellation|adr|nights?|guests?)\b',
    re.IGNORECASE,
)


def extract_entities(question: str) -> dict:
    temporal = [m.group(0).lower() for m in _TEMPORAL.finditer(question)]
    limits = [m.group(0).lower() for m in _LIMIT.finditer(question)]
    metrics = [m.group(0).lower() for m in _METRIC.finditer(question)]
    # Capitalised words likely to be location/property names
    locations = re.findall(r'\b[A-Z][a-z]{2,}\b', question)
    return {
        "temporal": sorted(set(temporal)),
        "limits": sorted(set(limits)),
        "metrics": sorted(set(metrics)),
        "locations": sorted(set(locations)),
    }


def _entities_compatible(e1: dict, e2: dict) -> bool:
    """True if entities are identical enough for Tier 1 exact reuse."""
    return (
        e1["temporal"] == e2["temporal"]
        and e1["limits"] == e2["limits"]
        and e1["locations"] == e2["locations"]
    )


# ── Core lookup ───────────────────────────────────────────────────────────────

def find_similar(question: str, connection_id: str) -> Optional[dict]:
    """
    Search query_history for a semantically similar verified or corrected query.
    Returns dict with tier, cached_sql, similarity, history_id, correction_note — or None.

    Eligibility: verified=TRUE (thumbs up) OR correction_note IS NOT NULL (thumbs down with note).
    If correction_note present → always Tier 2 so sql_modifier can apply the fix.
    """
    try:
        embedding = _get_embedder().embed_one(question)
        new_entities = extract_entities(question)

        conn = _get_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, question, generated_sql, correction_note,
                           1 - (question_embedding <=> %s::vector) AS similarity
                    FROM query_history
                    WHERE connection_id = %s
                      AND (verified = TRUE OR correction_note IS NOT NULL)
                      AND generated_sql IS NOT NULL
                      AND question_embedding IS NOT NULL
                    ORDER BY question_embedding <=> %s::vector
                    LIMIT 5
                    """,
                    (str(embedding), connection_id, str(embedding)),
                )
                rows = cur.fetchall()
        conn.close()

        if not rows:
            return None

        best = dict(rows[0])
        sim = float(best["similarity"])
        correction_note = best.get("correction_note")

        logger.info("[ECHO] Best match sim=%.3f correction=%s for: %s", sim, bool(correction_note), question[:60])

        if sim < TIER2_THRESHOLD:
            return None

        cached_entities = extract_entities(best["question"] or "")
        entities_match = _entities_compatible(new_entities, cached_entities)

        # If there's a correction note, force Tier 2 regardless of similarity
        if correction_note:
            logger.info("[ECHO] Tier 2 forced (correction note present, sim=%.3f)", sim)
            return {
                "tier": 2,
                "cached_sql": best["generated_sql"],
                "similarity": sim,
                "history_id": best["id"],
                "cached_question": best["question"],
                "correction_note": correction_note,
            }

        if sim >= TIER1_THRESHOLD and entities_match:
            logger.info("[ECHO] Tier 1 hit (sim=%.3f) — exact recycle", sim)
            return {
                "tier": 1,
                "cached_sql": best["generated_sql"],
                "similarity": sim,
                "history_id": best["id"],
                "cached_question": best["question"],
                "correction_note": None,
            }
        else:
            logger.info(
                "[ECHO] Tier 2 hit (sim=%.3f, entities_match=%s) — SQL modifier",
                sim, entities_match,
            )
            return {
                "tier": 2,
                "cached_sql": best["generated_sql"],
                "similarity": sim,
                "history_id": best["id"],
                "cached_question": best["question"],
                "correction_note": None,
            }

    except Exception as exc:
        logger.warning("[ECHO] Lookup failed: %s", exc)
        return None


def find_few_shot_examples(question: str, connection_id: str, limit: int = 3) -> list[dict]:
    """
    Return up to `limit` verified Q+SQL pairs for few-shot injection into SQL generation.
    Uses a lower similarity threshold (0.50) than ECHO for wider topical coverage.
    Returns: [{"id": int, "question": str, "generated_sql": str, "similarity": float}]
    """
    try:
        embedding = _get_embedder().embed_one(question)
        conn = _get_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, question, generated_sql,
                           1 - (question_embedding <=> %s::vector) AS similarity
                    FROM query_history
                    WHERE connection_id = %s
                      AND verified = TRUE
                      AND generated_sql IS NOT NULL
                      AND question_embedding IS NOT NULL
                    ORDER BY question_embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (str(embedding), connection_id, str(embedding), limit),
                )
                rows = cur.fetchall()
        conn.close()
        # Filter out near-duplicate noise below 0.50 similarity
        results = [dict(r) for r in rows if float(r["similarity"]) >= 0.50]
        logger.info("[ECHO] Found %d few-shot examples for: %s", len(results), question[:60])
        return results
    except Exception as exc:
        logger.warning("[ECHO] find_few_shot_examples failed: %s", exc)
        return []


def save_embedding(history_id: int, question: str, echo_tier: int) -> None:
    """Embed the question and save to query_history.question_embedding."""
    try:
        embedding = _get_embedder().embed_one(question)
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE query_history SET question_embedding = %s::vector, echo_tier = %s WHERE id = %s",
                    (str(embedding), echo_tier, history_id),
                )
        conn.close()
        logger.info("[ECHO] Saved embedding for history_id=%d", history_id)
    except Exception as exc:
        logger.warning("[ECHO] Failed to save embedding: %s", exc)


def save_to_history(
    connection_id: str,
    session_id: Optional[str],
    question: str,
    sql: str,
    echo_tier: int,
    rows_returned: int,
    processing_time_ms: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    cost_usd: float = 0.0,
    retry_count: int = 0,
    few_shot_used: bool = False,
) -> Optional[int]:
    """Insert a new query_history row with embedding and token/cost data. Returns new row id."""
    try:
        embedding = _get_embedder().embed_one(question)
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO query_history
                        (connection_id, session_id, question, generated_sql,
                         was_successful, rows_returned, execution_time_ms,
                         llm_model_used, question_embedding, echo_tier,
                         input_tokens, output_tokens, cache_read_tokens,
                         cache_write_tokens, cost_usd, retry_count, few_shot_used)
                    VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s, %s::vector, %s,
                            %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        connection_id, session_id, question, sql,
                        rows_returned, processing_time_ms,
                        "claude-sonnet-4-5", str(embedding), echo_tier,
                        input_tokens, output_tokens, cache_read_tokens,
                        cache_write_tokens, cost_usd, retry_count, few_shot_used,
                    ),
                )
                row_id = cur.fetchone()[0]
        conn.close()
        logger.info("[ECHO] Saved to history id=%d tier=%d cost=$%.5f", row_id, echo_tier, cost_usd)
        return row_id
    except Exception as exc:
        logger.warning("[ECHO] Failed to save history: %s", exc)
        return None
