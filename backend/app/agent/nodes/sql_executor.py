"""
Node 3 — sql_executor
Runs the generated SQL against the configured database.
Captures errors for the rewriter node.
"""
import asyncio
import logging
import psycopg2
import psycopg2.extras

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.agent.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)


def _get_connection_string(connection_id: str) -> str:
    """Fetch connection string from db_connections table."""
    return asyncio.run(_async_get_connection_string(connection_id))


async def _async_get_connection_string(connection_id: str) -> str:
    """Async helper to fetch connection string."""
    engine = create_async_engine(settings.datapilot_db_url, echo=False)
    async with AsyncSession(engine) as session:
        result = await session.execute(
            text("SELECT connection_string_encrypted FROM db_connections WHERE id = :id"),
            {"id": connection_id}
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"Connection {connection_id} not found")
        return row[0]


def _rows_to_dicts(cursor) -> list[dict]:
    cols = [desc[0] for desc in cursor.description] if cursor.description else []
    return [dict(zip(cols, row)) for row in (cursor.fetchall() or [])]


def sql_executor(state: AgentState) -> AgentState:
    sql = state.get("sql_query", "").strip()
    connection_id = state.get("connection_id")

    if not sql:
        return {
            **state,
            "sql_error": "Empty SQL query",
            "execution_success": False,
            "query_result": [],
        }

    if not connection_id:
        return {
            **state,
            "sql_error": "No connection_id in state",
            "execution_success": False,
            "query_result": [],
        }

    logger.info("[sql_executor] Executing: %s", sql[:200])

    conn = None
    try:
        # Get connection string from db_connections table
        connection_string = _get_connection_string(connection_id)
        conn = psycopg2.connect(connection_string)
        conn.set_session(readonly=True, autocommit=False)

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET statement_timeout = {settings.sql_query_timeout_seconds * 1000}")
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]

        logger.info("[sql_executor] Returned %d rows", len(rows))
        return {
            **state,
            "query_result": rows,
            "sql_error": None,
            "execution_success": True,
        }
    except Exception as exc:
        err = str(exc)
        logger.warning("[sql_executor] SQL error: %s", err)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return {
            **state,
            "query_result": [],
            "sql_error": err,
            "execution_success": False,
        }
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


