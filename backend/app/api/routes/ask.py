"""DataPilot — /ask Endpoint"""
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.core.embedding import SchemaEmbeddingPipeline
from app.core.llm import get_llm_client
from app.core.sql_generator import SQLGenerator
from app.models.schemas import AskRequest, AskResponse, ErrorResponse, SQLResult

router = APIRouter()
logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


def _get_engine():
    return create_async_engine(settings.datapilot_db_url, echo=False)


def _execute_sql_sync(connection_string: str, sql: str, max_rows: int) -> SQLResult:
    start = time.time()
    conn = psycopg2.connect(connection_string)
    conn.set_session(readonly=True, autocommit=False)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET statement_timeout = {settings.sql_query_timeout_seconds * 1000}")
            cur.execute(sql)
            raw_rows = cur.fetchmany(max_rows)
        elapsed_ms = (time.time() - start) * 1000
        rows = [{k: str(v) if v is not None else None for k, v in dict(r).items()} for r in raw_rows]
        return SQLResult(sql=sql, rows=rows, row_count=len(rows),
                         columns=list(rows[0].keys()) if rows else [],
                         execution_time_ms=round(elapsed_ms, 2))
    finally:
        conn.close()


@router.post("", response_model=AskResponse, responses={400: {"model": ErrorResponse}})
async def ask_question(request: AskRequest):
    import asyncio
    options = request.options
    max_rows = options.max_rows if options else 100
    session_id = request.session_id or str(uuid.uuid4())
    engine = _get_engine()
    total_start = time.time()

    async with AsyncSession(engine) as db_session:
        result = await db_session.execute(
            text("SELECT * FROM db_connections WHERE id = :id AND is_active = true"),
            {"id": request.connection_id},
        )
        conn_row = result.mappings().fetchone()
        if not conn_row:
            raise HTTPException(status_code=404,
                detail=f"Connection {request.connection_id} not found. Run POST /connect first.")
        if not conn_row["schema_indexed"]:
            raise HTTPException(status_code=400, detail="Schema not yet indexed. Please reconnect.")

        pipeline = SchemaEmbeddingPipeline(db_session=db_session)
        chunks = await pipeline.search_relevant_tables(
            connection_id=request.connection_id, question=request.question, top_k=5)
        if not chunks:
            raise HTTPException(status_code=400, detail="No schema found. Try reconnecting.")

        schema_context = "\n\n---\n\n".join(chunks)
        llm_client = get_llm_client()
        generator = SQLGenerator(llm_client=llm_client, max_rows=max_rows)
        gen_result = generator.generate(question=request.question, schema_context=schema_context)

        if not gen_result.can_answer or not gen_result.sql:
            await _log_query(db_session, request.connection_id, session_id, request.question,
                             None, False, "LLM could not generate SQL", gen_result.model)
            return AskResponse(
                question=request.question,
                answer="I couldn't generate a SQL query for this question. The schema might not contain the relevant data.",
                session_id=session_id, query_id=-1, llm_model=gen_result.model,
                total_time_ms=round((time.time() - total_start) * 1000, 2))

        loop = asyncio.get_event_loop()
        try:
            sql_result = await loop.run_in_executor(
                _executor, _execute_sql_sync,
                conn_row["connection_string_encrypted"], gen_result.sql, max_rows)
        except Exception as e:
            await _log_query(db_session, request.connection_id, session_id, request.question,
                             gen_result.sql, False, str(e), gen_result.model)
            raise HTTPException(status_code=422, detail=f"SQL execution failed: {str(e)}")

        total_ms = round((time.time() - total_start) * 1000, 2)
        answer = ("The query returned no results." if sql_result.row_count == 0
                  else f"Found {sql_result.row_count} result(s).")

        query_id = await _log_query(db_session, request.connection_id, session_id,
                                    request.question, gen_result.sql, True, None,
                                    gen_result.model, sql_result.row_count, sql_result.execution_time_ms)

        return AskResponse(question=request.question, answer=answer,
                           sql_result=sql_result, session_id=session_id,
                           query_id=query_id, llm_model=gen_result.model, total_time_ms=total_ms)


async def _log_query(session, connection_id, session_id, question, sql,
                     success, error, model, rows=None, exec_ms=None) -> int:
    result = await session.execute(
        text("""
            INSERT INTO query_history
                (connection_id, session_id, question, generated_sql, was_successful,
                 error_message, rows_returned, execution_time_ms, llm_model_used)
            VALUES (:conn_id, :sess_id, :question, :sql, :success, :error, :rows, :exec_ms, :model)
            RETURNING id
        """),
        {"conn_id": connection_id, "sess_id": session_id, "question": question,
         "sql": sql, "success": success, "error": error, "rows": rows,
         "exec_ms": exec_ms, "model": model},
    )
    await session.commit()
    row = result.fetchone()
    return row[0] if row else -1
