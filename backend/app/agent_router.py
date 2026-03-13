"""
DataPilot Phase 2 — FastAPI Router
POST /agent/ask — full agent pipeline with ECHO semantic cache
"""
import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.agent.graph.agent_graph import agent
from app.core.conversation import get_history, save_turn
from app.core.cost import aggregate_tokens, compute_cost_usd
from app.core.echo import save_to_history
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])
limiter = Limiter(key_func=get_remote_address)


class AgentAskRequest(BaseModel):
    connection_id: str = Field(..., description="Database connection ID from POST /connect")
    question: str = Field(..., min_length=3, description="Natural language analytics question")
    session_id: Optional[str] = Field(None, description="Session ID for multi-turn conversation")


class SubQuestionResult(BaseModel):
    sub_question: str
    sql: str
    row_count: int
    execution_success: bool
    retries: int


class ChartSuggestion(BaseModel):
    type: str
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    group_by: Optional[str] = None
    reason: str


class AgentAskResponse(BaseModel):
    question: str
    sub_questions: list[str]
    narrative: str
    chart_suggestion: ChartSuggestion
    data: list[dict[str, Any]]
    results: list[SubQuestionResult]
    total_rows: int
    sub_question_count: int
    processing_time_ms: int
    session_id: Optional[str] = None
    requires_new_query: Optional[bool] = None
    echo_tier: Optional[int] = None
    echo_similarity: Optional[float] = None
    cost_usd: Optional[float] = None
    total_tokens: Optional[int] = None


@router.post("/ask", response_model=AgentAskResponse, summary="Multi-step analytics agent with ECHO cache")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def agent_ask(request: Request, body: AgentAskRequest):
    print(f"=== AGENT ASK === connection_id: {body.connection_id}, question: {body.question}")
    start = time.perf_counter()
    logger.info("[/agent/ask] Q: %s | conn: %s | session: %s", body.question, body.connection_id, body.session_id)

    conversation_history: list[dict] = []
    if body.session_id:
        conversation_history = get_history(body.session_id)
        logger.info("[/agent/ask] Loaded %d history turns", len(conversation_history))

    initial_state = {
        "connection_id": body.connection_id,
        "original_question": body.question,
        "session_id": body.session_id,
        "conversation_history": conversation_history,
        "sub_questions": [],
        "current_sub_q_index": 0,
        "all_results": [],
        "retry_count": 0,
        "requires_new_query": True,
        "echo_tier": None,
        "echo_cached_sql": None,
        "echo_cached_question": None,
        "echo_similarity": None,
        "echo_history_id": None,
        "echo_correction_note": None,
        "few_shot_example_ids": [],
        "token_tracker": {},
        "execution_success": False,
        "sql_error": None,
        "query_result": [],
        "analysis_result": None,
        "narrative": "",
        "chart_suggestion": {},
        "final_response": {},
        "error": None,
    }

    try:
        final_state = agent.invoke(initial_state)
        if final_state is None:
            raise HTTPException(status_code=500, detail="Agent returned None")
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        logger.error("[/agent/ask] Pipeline crashed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {exc}")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    final: dict = final_state.get("final_response", {})
    if not final:
        raise HTTPException(status_code=500, detail="Agent produced no output")

    echo_tier = final_state.get("echo_tier", 3)

    # Compute token totals and cost
    token_tracker = final_state.get("token_tracker") or {}
    token_totals = aggregate_tokens(token_tracker)
    cost_usd = compute_cost_usd(token_tracker)
    total_tokens = sum(token_totals.values())
    retry_count = final_state.get("retry_count", 0)
    few_shot_ids = final_state.get("few_shot_example_ids") or []

    logger.info(
        "[/agent/ask] cost=$%.5f tokens=%d (in=%d out=%d cr=%d cw=%d) retries=%d few_shot=%d",
        cost_usd, total_tokens,
        token_totals["input"], token_totals["output"],
        token_totals["cache_read"], token_totals["cache_write"],
        retry_count, len(few_shot_ids),
    )

    # Save to ECHO history (best-effort, non-blocking)
    if final.get("data") is not None:
        all_results = final_state.get("all_results", [])
        best_sql = ""
        for r in all_results:
            if r.get("execution_success") and r.get("sql"):
                best_sql = r["sql"]
                break
        if best_sql:
            save_to_history(
                connection_id=body.connection_id,
                session_id=body.session_id,
                question=body.question,
                sql=best_sql,
                echo_tier=echo_tier or 3,
                rows_returned=final.get("total_rows", 0),
                processing_time_ms=elapsed_ms,
                input_tokens=token_totals["input"],
                output_tokens=token_totals["output"],
                cache_read_tokens=token_totals["cache_read"],
                cache_write_tokens=token_totals["cache_write"],
                cost_usd=cost_usd,
                retry_count=retry_count,
                few_shot_used=bool(few_shot_ids),
            )

    # Save conversation turn
    if body.session_id:
        try:
            save_turn(
                session_id=body.session_id,
                connection_id=body.connection_id,
                question=body.question,
                narrative=final_state.get("narrative", ""),
                data=final.get("data", []),
            )
        except Exception as exc:
            logger.warning("[/agent/ask] Failed to save conversation turn: %s", exc)

    results_out: list[SubQuestionResult] = []
    for r in final.get("results", []):
        analysis = r.get("analysis") or {}
        results_out.append(SubQuestionResult(
            sub_question=r.get("sub_question", ""),
            sql=r.get("sql", ""),
            row_count=analysis.get("row_count", 0),
            execution_success=r.get("execution_success", False),
            retries=r.get("retries", 0),
        ))

    cs = final.get("chart_suggestion", {})
    chart_out = ChartSuggestion(
        type=cs.get("type", "table"),
        x_axis=cs.get("x_axis"),
        y_axis=cs.get("y_axis"),
        group_by=cs.get("group_by"),
        reason=cs.get("reason", ""),
    )

    response = AgentAskResponse(
        question=final.get("question", body.question),
        sub_questions=final.get("sub_questions", []),
        narrative=final.get("narrative", ""),
        chart_suggestion=chart_out,
        data=final.get("data", []),
        results=results_out,
        total_rows=final.get("total_rows", 0),
        sub_question_count=final.get("sub_question_count", 0),
        processing_time_ms=elapsed_ms,
        session_id=body.session_id,
        requires_new_query=final_state.get("requires_new_query", True),
        echo_tier=echo_tier,
        echo_similarity=final_state.get("echo_similarity"),
        cost_usd=round(cost_usd, 6),
        total_tokens=total_tokens,
    )

    logger.info("[/agent/ask] Done in %dms | tier=%s | rows=%d", elapsed_ms, echo_tier, response.total_rows)
    return response
