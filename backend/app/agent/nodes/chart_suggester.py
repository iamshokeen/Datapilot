"""
Node 7 — chart_suggester
Analyses the shape of the data and recommends the most appropriate
chart type with axis mappings.
"""
import logging
from typing import Any

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

# Chart type decision rules (order matters — first match wins)
_RULES = [
    # (condition_fn, chart_type, reason_template)
    # Time-series first — date columns always → line
    (
        lambda cols, numeric, cat, rows: len(rows) > 1 and any(
            "date" in c.lower() or "month" in c.lower() or "year" in c.lower() or "week" in c.lower()
            for c in cols
        ),
        "line",
        "Time-series data is best visualised as a line chart to show trends over time.",
    ),
    # Pie before bar — more specific (pie is a subset of bar's conditions)
    (
        lambda cols, numeric, cat, rows: len(cat) == 1 and len(numeric) == 1 and 2 <= len(rows) <= 8,
        "pie",
        "Small number of categories with a single metric suits a pie chart for part-of-whole analysis.",
    ),
    (
        lambda cols, numeric, cat, rows: len(cat) == 1 and len(numeric) >= 1 and len(rows) <= 20,
        "bar",
        "Categorical comparison with a single grouping variable suits a bar chart.",
    ),
    (
        lambda cols, numeric, cat, rows: len(numeric) >= 2,
        "scatter",
        "Two or more numeric dimensions suggest a scatter plot to explore correlations.",
    ),
    (
        lambda cols, numeric, cat, rows: len(cat) >= 2 and len(numeric) >= 1,
        "grouped_bar",
        "Multiple categorical groupings with a numeric metric suit a grouped bar chart.",
    ),
]

_FALLBACK = {
    "type": "table",
    "x_axis": None,
    "y_axis": None,
    "group_by": None,
    "reason": "Data structure does not match a standard chart pattern; a table is recommended.",
}


def _infer_axes(cols: list[str], numeric: list[str], cat: list[str], chart_type: str) -> dict:
    date_cols = [c for c in cols if any(k in c.lower() for k in ("date", "month", "year", "week", "day"))]
    x = date_cols[0] if date_cols else (cat[0] if cat else (numeric[0] if numeric else None))
    y = numeric[0] if numeric else None
    group = cat[1] if len(cat) > 1 else None
    return {"x_axis": x, "y_axis": y, "group_by": group}


def chart_suggester(state: AgentState) -> AgentState:
    all_results: list[dict] = state.get("all_results", [])

    # Use the first (or largest) result set for chart inference
    best = max(
        all_results,
        key=lambda r: (r.get("analysis") or {}).get("row_count", 0),
        default=None,
    )

    if not best:
        return {**state, "chart_suggestion": _FALLBACK}

    analysis: dict = best.get("analysis") or {}
    rows: list[dict] = analysis.get("rows", [])
    columns: list[str] = analysis.get("columns", list(rows[0].keys()) if rows else [])

    try:
        import pandas as pd
        import numpy as np

        df = pd.DataFrame(rows)
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    except Exception:
        # Fallback: guess by column name heuristics
        numeric_cols = [c for c in columns if any(
            k in c.lower() for k in ("count", "total", "revenue", "amount", "price", "rate", "num", "avg", "sum")
        )]
        cat_cols = [c for c in columns if c not in numeric_cols]

    suggestion = _FALLBACK.copy()
    for condition_fn, chart_type, reason in _RULES:
        try:
            if condition_fn(columns, numeric_cols, cat_cols, rows):
                axes = _infer_axes(columns, numeric_cols, cat_cols, chart_type)
                suggestion = {"type": chart_type, "reason": reason, **axes}
                break
        except Exception:
            continue

    logger.info("[chart_suggester] Suggested: %s", suggestion.get("type"))
    return {**state, "chart_suggestion": suggestion}

