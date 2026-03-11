"""
DataPilot — LangGraph Agent Graph with ECHO

Flow (new queries only):
  query_planner
      ↓ requires_new_query=True
  echo_lookup
      ├── Tier 1 (exact match)  → sql_executor  (skip generation)
      ├── Tier 2 (modify)       → sql_modifier → sql_executor
      └── Tier 3 (no match)     → sql_generator → sql_executor

  query_planner
      ↓ requires_new_query=False
  python_analyst  (reuse previous data)
"""
import logging

from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import (
    query_planner,
    echo_lookup,
    sql_generator,
    sql_modifier,
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


def route_after_planner(state: AgentState) -> str:
    if state.get("requires_new_query", True):
        return "echo_lookup"
    logger.info("[router] Re-using previous data → python_analyst")
    return "python_analyst"


def route_after_echo(state: AgentState) -> str:
    tier = state.get("echo_tier", 3)
    if tier == 1:
        logger.info("[router] ECHO Tier 1 — exact recycle → sql_executor")
        return "sql_executor"
    if tier == 2:
        logger.info("[router] ECHO Tier 2 — modify → sql_modifier")
        return "sql_modifier"
    logger.info("[router] ECHO Tier 3 — full generation → sql_generator")
    return "sql_generator"


def route_after_executor(state: AgentState) -> str:
    if not state:
        return "accumulate_result"
    if state.get("execution_success"):
        return "python_analyst"
    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        logger.info("[router] SQL failed (retry %d/%d) → sql_rewriter", retry_count, MAX_RETRIES)
        return "sql_rewriter"
    logger.warning("[router] Max retries → accumulate_result (with error)")
    return "accumulate_result"


def route_after_accumulate(state: AgentState) -> str:
    if not state:
        return "insight_narrator"
    sub_questions = state.get("sub_questions", [])
    idx = state.get("current_sub_q_index", 0)
    if idx < len(sub_questions):
        logger.info("[router] Sub-question %d/%d → echo_lookup", idx + 1, len(sub_questions))
        return "echo_lookup"
    logger.info("[router] All sub-questions done → insight_narrator")
    return "insight_narrator"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("query_planner", query_planner)
    graph.add_node("echo_lookup", echo_lookup)
    graph.add_node("sql_generator", sql_generator)
    graph.add_node("sql_modifier", sql_modifier)
    graph.add_node("sql_executor", sql_executor)
    graph.add_node("sql_rewriter", sql_rewriter)
    graph.add_node("python_analyst", python_analyst)
    graph.add_node("accumulate_result", accumulate_result)
    graph.add_node("insight_narrator", insight_narrator)
    graph.add_node("chart_suggester", chart_suggester)
    graph.add_node("assemble_response", assemble_response)

    graph.set_entry_point("query_planner")

    graph.add_conditional_edges("query_planner", route_after_planner, {
        "echo_lookup": "echo_lookup",
        "python_analyst": "python_analyst",
    })

    graph.add_conditional_edges("echo_lookup", route_after_echo, {
        "sql_executor": "sql_executor",
        "sql_modifier": "sql_modifier",
        "sql_generator": "sql_generator",
    })

    graph.add_edge("sql_generator", "sql_executor")
    graph.add_edge("sql_modifier", "sql_executor")
    graph.add_edge("sql_rewriter", "sql_executor")
    graph.add_edge("python_analyst", "accumulate_result")
    graph.add_edge("insight_narrator", "chart_suggester")
    graph.add_edge("chart_suggester", "assemble_response")
    graph.add_edge("assemble_response", END)

    graph.add_conditional_edges("sql_executor", route_after_executor, {
        "python_analyst": "python_analyst",
        "sql_rewriter": "sql_rewriter",
        "accumulate_result": "accumulate_result",
    })

    graph.add_conditional_edges("accumulate_result", route_after_accumulate, {
        "echo_lookup": "echo_lookup",
        "insight_narrator": "insight_narrator",
    })

    return graph


def compile_agent():
    graph = build_graph()
    return graph.compile()


agent = compile_agent()
logger.info("[graph] DataPilot agent with ECHO compiled successfully")
