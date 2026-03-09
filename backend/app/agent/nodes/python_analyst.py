"""
Node 5 — python_analyst
Runs pandas on the SQL result to enrich it with aggregations, statistics,
and calculations that are easier to express in Python than in SQL.
"""
import logging
from typing import Any

from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def _safe_val(v: Any) -> Any:
    """Convert numpy/pandas types to native Python for JSON serialisation."""
    try:
        import numpy as np
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, np.ndarray):
            return v.tolist()
    except ImportError:
        pass
    return v


def python_analyst(state: AgentState) -> AgentState:
    rows: list[dict] = state.get("query_result", [])

    if not rows:
        return {**state, "analysis_result": {"rows": [], "stats": {}, "row_count": 0}}

    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        row_count = len(df)

        stats: dict[str, Any] = {"row_count": row_count}

        # Numeric summary
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            desc = df[numeric_cols].describe().to_dict()
            stats["numeric_summary"] = {
                col: {k: _safe_val(v) for k, v in col_stats.items()}
                for col, col_stats in desc.items()
            }

            # Top & bottom performers (first numeric col as value, first non-numeric as label)
            non_numeric_cols = df.select_dtypes(exclude="number").columns.tolist()
            if non_numeric_cols and numeric_cols:
                label_col = non_numeric_cols[0]
                value_col = numeric_cols[0]
                sorted_df = df[[label_col, value_col]].dropna().sort_values(
                    value_col, ascending=False
                )
                stats["top_5"] = sorted_df.head(5).to_dict(orient="records")
                stats["bottom_5"] = sorted_df.tail(5).to_dict(orient="records")

        # Categorical distributions (up to 3 cols, up to 10 unique values each)
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()[:3]
        if cat_cols:
            stats["distributions"] = {}
            for col in cat_cols:
                vc = df[col].value_counts().head(10)
                stats["distributions"][col] = {
                    str(k): _safe_val(v) for k, v in vc.items()
                }

        # Date-range detection
        for col in df.columns:
            if "date" in col.lower() or "time" in col.lower():
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce")
                    non_null = parsed.dropna()
                    if len(non_null):
                        stats["date_range"] = {
                            "column": col,
                            "min": str(non_null.min()),
                            "max": str(non_null.max()),
                        }
                        break
                except Exception:
                    pass

        analysis_result = {
            "rows": rows,
            "stats": stats,
            "row_count": row_count,
            "columns": list(df.columns),
        }

        logger.info(
            "[python_analyst] Analysed %d rows, %d numeric cols", row_count, len(numeric_cols)
        )
        return {**state, "analysis_result": analysis_result}

    except Exception as exc:
        logger.warning("[python_analyst] Analysis failed, passing raw rows: %s", exc)
        return {
            **state,
            "analysis_result": {
                "rows": rows,
                "stats": {"row_count": len(rows)},
                "row_count": len(rows),
                "error": str(exc),
            },
        }

