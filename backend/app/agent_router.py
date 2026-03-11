"""
DataPilot Phase 2 — FastAPI Router
New endpoint: POST /agent/ask
Existing /ask endpoint is untouched (backward compatible).
"""
import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.graph.agent_graph import agent
from app.core.conversation import get_history, save_turn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# ── Request / Response models ────────────────────────────────────────────────

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


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AgentAskResponse, summary="Multi-step analytics agent")
async def agent_ask(request: AgentAskRequest):
    """
    Runs the full LangGraph multi-step agent pipeline with multi-turn conversation support.

    Pass the same session_id across requests to maintain conversation context.
    The agent automatically classifies whether a follow-up question needs new SQL
    or can be answered from the previously fetched data.
    """
    print(f"=== AGENT ASK CALLED === connection_id: {request.connection_id}, question: {request.question}")
    start = time.perf_counter()
    logger.info(
        "[/agent/ask] Question: %s | connection_id: %s | session: %s",
        request.question, request.connection_id, request.session_id
    )

    # Load conversation history for multi-turn context
    conversation_history: list[dict] = []
    if request.session_id:
        conversation_history = get_history(request.session_id)
        logger.info("[/agent/ask] Loaded %d history turns", len(conversation_history))

    initial_state = {
        "connection_id": request.connection_id,
        "original_question": request.question,
        "session_id": request.session_id,
        "conversation_history": conversation_history,
        "sub_questions": [],
        "current_sub_q_index": 0,
        "all_results": [],
        "retry_count": 0,
        "requires_new_query": True,
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
        logger.info("[/agent/ask] Agent returned, type: %s", type(final_state))

        if final_state is None:
            logger.error("[/agent/ask] Agent returned None!")
            raise HTTPException(status_code=500, detail="Agent returned None - check logs for node errors")

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        logger.error("[/agent/ask] Agent pipeline crashed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {exc}")

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    final: dict = final_state.get("final_response", {})
    if not final:
        raise HTTPException(status_code=500, detail="Agent produced no output")

    # Save this turn to conversation history (non-blocking, best-effort)
    if request.session_id:
        try:
            save_turn(
                session_id=request.session_id,
                connection_id=request.connection_id,
                question=request.question,
                narrative=final_state.get("narrative", ""),
                data=final.get("data", []),
            )
        except Exception as exc:
            logger.warning("[/agent/ask] Failed to save conversation turn: %s", exc)

    # Build sub-question result summaries
    results_out: list[SubQuestionResult] = []
    for r in final.get("results", []):
        analysis = r.get("analysis") or {}
        results_out.append(
            SubQuestionResult(
                sub_question=r.get("sub_question", ""),
                sql=r.get("sql", ""),
                row_count=analysis.get("row_count", 0),
                execution_success=r.get("execution_success", False),
                retries=r.get("retries", 0),
            )
        )

    # Chart suggestion with fallback defaults
    cs = final.get("chart_suggestion", {})
    chart_out = ChartSuggestion(
        type=cs.get("type", "table"),
        x_axis=cs.get("x_axis"),
        y_axis=cs.get("y_axis"),
        group_by=cs.get("group_by"),
        reason=cs.get("reason", ""),
    )

    response = AgentAskResponse(
        question=final.get("question", request.question),
        sub_questions=final.get("sub_questions", []),
        narrative=final.get("narrative", ""),
        chart_suggestion=chart_out,
        data=final.get("data", []),
        results=results_out,
        total_rows=final.get("total_rows", 0),
        sub_question_count=final.get("sub_question_count", 0),
        processing_time_ms=elapsed_ms,
        session_id=request.session_id,
        requires_new_query=final_state.get("requires_new_query", True),
    )

    logger.info(
        "[/agent/ask] Done in %dms — %d rows, %d sub-questions, requires_new_query=%s",
        elapsed_ms, response.total_rows, response.sub_question_count, response.requires_new_query,
    )
    return response
