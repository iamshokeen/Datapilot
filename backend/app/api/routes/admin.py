"""
DataPilot Admin API — dashboard metrics, query history, and system stats.
All endpoints are prefixed with /admin.
"""
import json
import logging
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Query

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

LORE_PATH = Path(__file__).parent.parent.parent.parent / "knowledge" / "lore.json"


def _get_conn():
    return psycopg2.connect(
        host=settings.datapilot_db_host,
        port=settings.datapilot_db_port,
        dbname=settings.datapilot_db_name,
        user=settings.datapilot_db_user,
        password=settings.datapilot_db_password,
    )


# ── KPI Stats ─────────────────────────────────────────────────────────────────

@router.get("/stats", summary="Aggregate KPI stats")
def get_stats(days: int = Query(30, ge=1, le=365)):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) AS total_queries,
                        ROUND(100.0 * SUM(CASE WHEN was_successful THEN 1 ELSE 0 END)
                              / NULLIF(COUNT(*), 0), 1) AS success_rate_pct,
                        ROUND(AVG(cost_usd)::NUMERIC, 6) AS avg_cost_usd,
                        ROUND(SUM(cost_usd)::NUMERIC, 4) AS total_cost_usd,
                        ROUND(AVG(execution_time_ms)::NUMERIC, 0) AS avg_response_time_ms,
                        ROUND(100.0 * SUM(CASE WHEN echo_tier IN (1,2) THEN 1 ELSE 0 END)
                              / NULLIF(COUNT(*), 0), 1) AS echo_hit_rate_pct,
                        ROUND(100.0 * SUM(CASE WHEN retry_count > 0 THEN 1 ELSE 0 END)
                              / NULLIF(COUNT(*), 0), 1) AS retry_rate_pct,
                        ROUND(100.0 * SUM(CASE WHEN few_shot_used THEN 1 ELSE 0 END)
                              / NULLIF(COUNT(*), 0), 1) AS few_shot_rate_pct,
                        SUM(input_tokens) AS total_input_tokens,
                        SUM(output_tokens) AS total_output_tokens,
                        SUM(cache_read_tokens) AS total_cache_read_tokens,
                        SUM(cache_write_tokens) AS total_cache_write_tokens,
                        SUM(input_tokens + output_tokens + cache_read_tokens + cache_write_tokens) AS total_tokens,
                        SUM(CASE WHEN feedback = 'up' THEN 1 ELSE 0 END) AS thumbs_up,
                        SUM(CASE WHEN feedback = 'down' THEN 1 ELSE 0 END) AS thumbs_down,
                        SUM(CASE WHEN verified = TRUE THEN 1 ELSE 0 END) AS verified_count,
                        ROUND(AVG(retry_count)::NUMERIC, 2) AS avg_retries
                    FROM query_history
                    WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
                """, (str(days),))
                row = dict(cur.fetchone())

        # LORE entry count
        lore_count = 0
        try:
            lore_data = json.loads(LORE_PATH.read_text()) if LORE_PATH.exists() else {}
            lore_count = sum(len(v) for v in lore_data.values() if isinstance(v, list))
        except Exception:
            pass

        row["lore_entry_count"] = lore_count
        return row
    finally:
        conn.close()


# ── Time-series charts ─────────────────────────────────────────────────────────

@router.get("/chart/volume", summary="Daily query volume (line chart)")
def get_volume(days: int = Query(30, ge=1, le=365)):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        TO_CHAR(DATE(created_at), 'YYYY-MM-DD') AS day,
                        COUNT(*) AS queries,
                        SUM(CASE WHEN was_successful THEN 1 ELSE 0 END) AS successful,
                        SUM(CASE WHEN NOT was_successful THEN 1 ELSE 0 END) AS failed
                    FROM query_history
                    WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at)
                """, (str(days),))
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/chart/cost", summary="Daily cost over time (area chart)")
def get_cost(days: int = Query(30, ge=1, le=365)):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        TO_CHAR(DATE(created_at), 'YYYY-MM-DD') AS day,
                        ROUND(SUM(cost_usd)::NUMERIC, 5) AS total_cost,
                        ROUND(AVG(cost_usd)::NUMERIC, 5) AS avg_cost
                    FROM query_history
                    WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at)
                """, (str(days),))
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/chart/tokens", summary="Daily token breakdown (stacked area chart)")
def get_tokens(days: int = Query(30, ge=1, le=365)):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        TO_CHAR(DATE(created_at), 'YYYY-MM-DD') AS day,
                        SUM(input_tokens) AS input,
                        SUM(output_tokens) AS output,
                        SUM(cache_read_tokens) AS cache_read,
                        SUM(cache_write_tokens) AS cache_write
                    FROM query_history
                    WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at)
                """, (str(days),))
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/chart/echo-tiers", summary="ECHO tier distribution (pie chart)")
def get_echo_tiers(days: int = Query(30, ge=1, le=365)):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COALESCE(echo_tier, 3) AS tier,
                        COUNT(*) AS count
                    FROM query_history
                    WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
                    GROUP BY COALESCE(echo_tier, 3)
                    ORDER BY tier
                """, (str(days),))
                rows = [dict(r) for r in cur.fetchall()]
                tier_labels = {1: "Tier 1 — Exact", 2: "Tier 2 — Modified", 3: "Tier 3 — Full Gen"}
                return [{"name": tier_labels.get(int(r["tier"]), f"Tier {r['tier']}"), "value": r["count"]} for r in rows]
    finally:
        conn.close()


@router.get("/chart/response-time", summary="Daily avg response time (line chart)")
def get_response_time(days: int = Query(30, ge=1, le=365)):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        TO_CHAR(DATE(created_at), 'YYYY-MM-DD') AS day,
                        ROUND(AVG(execution_time_ms)::NUMERIC, 0) AS avg_ms,
                        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms)::NUMERIC, 0) AS p95_ms
                    FROM query_history
                    WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at)
                """, (str(days),))
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Query History Table ────────────────────────────────────────────────────────

@router.get("/queries", summary="Paginated recent query history")
def get_queries(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    days: int = Query(30, ge=1, le=365),
):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id,
                        LEFT(question, 120) AS question,
                        COALESCE(echo_tier, 3) AS echo_tier,
                        ROUND(cost_usd::NUMERIC, 5) AS cost_usd,
                        (input_tokens + output_tokens + cache_read_tokens + cache_write_tokens) AS total_tokens,
                        retry_count,
                        few_shot_used,
                        was_successful,
                        execution_time_ms,
                        feedback,
                        verified,
                        TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created_at
                    FROM query_history
                    WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (str(days), limit, offset))
                rows = [dict(r) for r in cur.fetchall()]

                # Total count for pagination
                cur.execute(
                    "SELECT COUNT(*) FROM query_history WHERE created_at >= NOW() - (%s || ' days')::INTERVAL",
                    (str(days),)
                )
                total = cur.fetchone()[0]

        return {"rows": rows, "total": total}
    finally:
        conn.close()


# ── Failures ──────────────────────────────────────────────────────────────────

@router.get("/top-failures", summary="Top failing questions")
def get_top_failures(limit: int = Query(10, ge=1, le=50)):
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        LEFT(question, 100) AS question,
                        COUNT(*) AS failure_count,
                        MAX(TO_CHAR(created_at, 'YYYY-MM-DD')) AS last_seen,
                        ROUND(AVG(retry_count)::NUMERIC, 1) AS avg_retries
                    FROM query_history
                    WHERE was_successful = FALSE
                    GROUP BY LEFT(question, 100)
                    ORDER BY failure_count DESC
                    LIMIT %s
                """, (limit,))
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── LORE ──────────────────────────────────────────────────────────────────────

@router.get("/lore", summary="LORE knowledge base contents")
def get_lore():
    try:
        if not LORE_PATH.exists():
            return {"entries": {}, "total_rules": 0}
        data = json.loads(LORE_PATH.read_text())
        total = sum(len(v) for v in data.values() if isinstance(v, list))
        return {"entries": data, "total_rules": total}
    except Exception as exc:
        logger.error("[admin/lore] Failed: %s", exc)
        return {"entries": {}, "total_rules": 0}
