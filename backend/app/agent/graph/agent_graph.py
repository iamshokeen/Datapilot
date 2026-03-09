"""
DataPilot Phase 2 — LangGraph Agent Graph
==========================================

Flow:
                        ┌─────────────────────────────────┐
                        │         query_planner           │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │         sql_generator           │◄──────────────────┐
                        └──────────────┬──────────────────┘                   │
                                       │                                       │
                        ┌──────────────▼──────────────────┐                   │
                        │         sql_executor            │                   │
                        └──────────────┬──────────────────┘                   │
                                       │                                       │
                           ┌───────────┴───────────┐                          │
                        success                  error                        │
                           │                       │                          │
                    ┌──────▼──────┐         ┌──────▼──────┐    retry < 2     │
                    │python_analyst│         │sql_rewriter  ├──────────────────┘
                    └──────┬──────┘         └──────┬──────┘
                           │                       │ retry >= 2
                           │               ┌───────▼───────────┐
                           │               │ accumulate (error)│
                           │               └───────────────────┘
                    ┌──────▼──────────────────────────────────┐
                    │         accumulate_result               │
                    └──────────────┬──────────────────────────┘
                                   │
                       ┌───────────┴───────────┐
                  more sub-qs             all done
                       │                       │
              (back to sql_generator)   ┌──────▼──────────────┐
                                        │  insight_narrator   │
                                        └──────┬──────────────┘
                                               │
                                        ┌──────▼──────────────┐
                                        │  chart_suggester    │
                                        └──────┬──────────────┘
                                               │
                                        ┌──────▼──────────────┐
                                        │  assemble_response  │
                                        └─────────────────────┘
"""
import logging

from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import (
    query_planner,
    sql_generator,
    sql_executor,
    sql_rewriter,
    python_analyst,
    insight_narrator,
    chart_suggester,
    accumulate_result,
    assemble_response,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


# ── Routing functions ────────────────────────────────────────────────────────

def route_after_executor(state: AgentState) -> str:
    """After SQL execution: success → python_analyst, failure → rewriter or give_up."""
    if not state:
        logger.error("[router] State is None in route_after_executor!")
        return "accumulate_result"

    if state.get("execution_success"):
        return "python_analyst"
    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        logger.info("[router] SQL failed (retry %d/%d) → sql_rewriter", retry_count, MAX_RETRIES)
        return "sql_rewriter"
    logger.warning("[router] Max retries reached → accumulate_result (with error)")
    return "accumulate_result"


def route_after_accumulate(state: AgentState) -> str:
    """After accumulating a sub-question result: more to do → sql_generator, else → narrate."""
    if not state:
        logger.error("[router] State is None in route_after_accumulate!")
        return "insight_narrator"

    sub_questions = state.get("sub_questions", [])
    idx = state.get("current_sub_q_index", 0)
    if idx < len(sub_questions):
        logger.info("[router] Sub-question %d/%d → sql_generator", idx + 1, len(sub_questions))
        return "sql_generator"
    logger.info("[router] All sub-questions done → insight_narrator")
    return "insight_narrator"


# ── Graph construction ───────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("query_planner", query_planner)
    graph.add_node("sql_generator", sql_generator)
    graph.add_node("sql_executor", sql_executor)
    graph.add_node("sql_rewriter", sql_rewriter)
    graph.add_node("python_analyst", python_analyst)
    graph.add_node("accumulate_result", accumulate_result)
    graph.add_node("insight_narrator", insight_narrator)
    graph.add_node("chart_suggester", chart_suggester)
    graph.add_node("assemble_response", assemble_response)

    # Entry point
    graph.set_entry_point("query_planner")

    # Linear edges
    graph.add_edge("query_planner", "sql_generator")
    graph.add_edge("sql_generator", "sql_executor")
    graph.add_edge("sql_rewriter", "sql_executor")        # rewriter feeds back into executor
    graph.add_edge("python_analyst", "accumulate_result")
    graph.add_edge("insight_narrator", "chart_suggester")
    graph.add_edge("chart_suggester", "assemble_response")
    graph.add_edge("assemble_response", END)

    # Conditional edges
    graph.add_conditional_edges(
        "sql_executor",
        route_after_executor,
        {
            "python_analyst": "python_analyst",
            "sql_rewriter": "sql_rewriter",
            "accumulate_result": "accumulate_result",
        },
    )

    graph.add_conditional_edges(
        "accumulate_result",
        route_after_accumulate,
        {
            "sql_generator": "sql_generator",
            "insight_narrator": "insight_narrator",
        },
    )

    return graph


def compile_agent():
    """Compile and return the runnable agent."""
    graph = build_graph()
    return graph.compile()


# Module-level compiled agent (imported by the FastAPI router)
agent = compile_agent()

logger.info("[graph] DataPilot Phase 2 agent compiled successfully")

