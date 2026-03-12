"""
Node 2 — sql_generator
Wraps the existing sql_generator module.
Picks the current sub-question from state, fetches few-shot examples (Tier 3 only),
and generates SQL. Captures token usage into state.token_tracker.
"""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.agent.state import AgentState
from app.config import settings
from app.core.echo import find_few_shot_examples
from app.core.embedding import SchemaEmbeddingPipeline
from app.core.llm import get_llm_client
from app.core.sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


def sql_generator(state: AgentState) -> AgentState:
    sub_questions: list[str] = state.get("sub_questions", [])
    idx: int = state.get("current_sub_q_index", 0)
    question = sub_questions[idx] if idx < len(sub_questions) else state["original_question"]

    sql_error = state.get("sql_error")
    retry_count = state.get("retry_count", 0)

    if sql_error and retry_count > 0:
        logger.info("[sql_generator] Skipping re-gen (retry %d handled by rewriter)", retry_count)
        return state

    logger.info("[sql_generator] Generating SQL for: %s", question)
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                _generate_sql_with_context(state["connection_id"], question),
            )
            sql, usage, few_shot_ids = future.result()

        token_tracker = dict(state.get("token_tracker") or {})
        token_tracker["sql_generator"] = usage

        logger.info("[sql_generator] SQL ready | tokens in=%d out=%d", usage["input"], usage["output"])
        return {
            **state,
            "sql_query": sql,
            "sql_error": None,
            "execution_success": False,
            "token_tracker": token_tracker,
            "few_shot_example_ids": few_shot_ids,
        }
    except Exception as exc:
        logger.error("[sql_generator] Generation failed: %s", exc)
        return {**state, "sql_query": "", "sql_error": str(exc), "execution_success": False}


async def _generate_sql_with_context(connection_id: str, question: str) -> tuple[str, dict, list[int]]:
    """Generate SQL using schema context + few-shot examples. Returns (sql, usage, few_shot_ids)."""
    engine = create_async_engine(settings.datapilot_db_url, echo=False)

    async with AsyncSession(engine) as db_session:
        pipeline = SchemaEmbeddingPipeline(db_session=db_session)
        chunks = await pipeline.search_relevant_tables(
            connection_id=connection_id, question=question, top_k=5
        )

        if not chunks:
            raise ValueError("No schema context found. Try reconnecting.")

        schema_context = "\n\n---\n\n".join(chunks)

    # Fetch few-shot examples (sync, outside the async session)
    few_shot_examples = find_few_shot_examples(question, connection_id, limit=3)
    few_shot_ids = [ex["id"] for ex in few_shot_examples]

    llm_client = get_llm_client()
    generator = SQLGenerator(llm_client=llm_client, max_rows=100)
    gen_result = generator.generate_with_examples(
        question=question,
        schema_context=schema_context,
        few_shot_examples=few_shot_examples,
    )

    if not gen_result.can_answer or not gen_result.sql:
        raise ValueError("LLM could not generate SQL for this question")

    return gen_result.sql, gen_result.usage, few_shot_ids
