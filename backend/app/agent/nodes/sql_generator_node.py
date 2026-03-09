"""
Node 2 — sql_generator
Wraps the existing sql_generator module (Phase 1).
Picks the current sub-question from state and generates SQL.
"""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.agent.state import AgentState
from app.config import settings
from app.core.embedding import SchemaEmbeddingPipeline
from app.core.llm import get_llm_client
from app.core.sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


async def sql_generator(state: AgentState) -> AgentState:
    sub_questions: list[str] = state.get("sub_questions", [])
    idx: int = state.get("current_sub_q_index", 0)
    question = sub_questions[idx] if idx < len(sub_questions) else state["original_question"]

    sql_error = state.get("sql_error")
    retry_count = state.get("retry_count", 0)

    if sql_error and retry_count > 0:
        # We are in a retry — the sql_rewriter has already fixed the SQL,
        # so we skip re-generation here (sql_rewriter writes directly to sql_query).
        logger.info("[sql_generator] Skipping re-gen (retry %d handled by rewriter)", retry_count)
        return state

    logger.info("[sql_generator] Generating SQL for: %s", question)
    try:
        # Now we can await directly since this node is async
        sql = await _generate_sql_with_context(state["connection_id"], question)
        logger.info("[sql_generator] SQL: %s", sql)
        return {
            **state,
            "sql_query": sql,
            "sql_error": None,
            "execution_success": False,
        }
    except Exception as exc:
        logger.error("[sql_generator] Generation failed: %s", exc)
        return {**state, "sql_query": "", "sql_error": str(exc), "execution_success": False}


async def _generate_sql_with_context(connection_id: str, question: str) -> str:
    """Generate SQL using schema context from embeddings (same as Phase 1)."""
    engine = create_async_engine(settings.datapilot_db_url, echo=False)

    async with AsyncSession(engine) as db_session:
        # Fetch schema context from embeddings
        pipeline = SchemaEmbeddingPipeline(db_session=db_session)
        chunks = await pipeline.search_relevant_tables(
            connection_id=connection_id, question=question, top_k=5
        )

        if not chunks:
            raise ValueError("No schema context found. Try reconnecting.")

        schema_context = "\n\n---\n\n".join(chunks)

        # Generate SQL using the Phase 1 SQLGenerator
        llm_client = get_llm_client()
        generator = SQLGenerator(llm_client=llm_client, max_rows=100)
        gen_result = generator.generate(question=question, schema_context=schema_context)

        if not gen_result.can_answer or not gen_result.sql:
            raise ValueError("LLM could not generate SQL for this question")

        return gen_result.sql


