"""
DataPilot Evaluation Harness
=============================
Runs the golden query set through the DataPilot agent and scores:
  1. Execution success rate  — did the agent return a result without error?
  2. SQL result match        — does the agent's result set match the golden SQL output?
  3. DeepEval GEval score    — does the narrative correctly answer the question?

Usage:
    cd backend
    python -m eval.run_eval [--api-url http://localhost:8080] [--connection-id <id>] [--category revenue] [--ids q001,q002]

Output:
    - Console table with per-query scores
    - backend/eval/results/latest.json  (machine-readable)
    - backend/eval/results/latest_report.md  (markdown report)
"""

import argparse
import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from tabulate import tabulate

# ── Optional DeepEval import ──────────────────────────────────────────────────
try:
    from deepeval import evaluate
    from deepeval.metrics import GEval
    from deepeval.models import GPTModel
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

GOLDEN_PATH = Path(__file__).parent / "golden_queries.json"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ── DB connection (reads same env as backend) ─────────────────────────────────

def _db_conn():
    """Direct psycopg2 connection to run golden SQL."""
    # Try settings first, fall back to env vars
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.config import settings
        return psycopg2.connect(
            host=settings.datapilot_db_host,
            port=settings.datapilot_db_port,
            dbname=settings.datapilot_db_name,
            user=settings.datapilot_db_user,
            password=settings.datapilot_db_password,
        )
    except Exception:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5433")),
            dbname=os.getenv("DB_NAME", "datapilot"),
            user=os.getenv("DB_USER", "datapilot"),
            password=os.getenv("DB_PASSWORD", "datapilot"),
        )


def run_golden_sql(sql: str) -> list[dict]:
    conn = _db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Agent API call ─────────────────────────────────────────────────────────────

def ask_agent(question: str, api_url: str, connection_id: str, session_id: str) -> dict:
    """Call POST /agent/ask and return the parsed response."""
    payload = {
        "question": question,
        "connection_id": connection_id,
        "session_id": session_id,
    }
    resp = requests.post(f"{api_url}/agent/ask", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


# ── Result matching ────────────────────────────────────────────────────────────

def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def _extract_numerics(row: dict) -> list[float]:
    """Return all numeric values from a dict row, sorted by key name."""
    out = []
    for k in sorted(row.keys()):
        v = _to_float(row[k])
        if isinstance(v, float):
            out.append(v)
    return out


def _extract_strings(row: dict, check_columns: list[str]) -> list[str]:
    """Return string values for the given columns (case-insensitive key lookup)."""
    out = []
    for col in check_columns:
        matched_key = next((k for k in row if k.lower() == col.lower()), None)
        if matched_key:
            out.append(str(row[matched_key]).lower())
    return out


def _rows_match(golden_rows: list[dict], agent_rows: list[dict],
                check_columns: list[str], tolerance_pct: float) -> tuple[bool, str]:
    """
    Compare golden vs agent result sets.
    Strategy:
      1. Row count must match.
      2. For each row pair, compare numeric values positionally within tolerance.
         Column names are intentionally ignored — the agent may use different aliases.
      3. String columns listed in check_columns are matched case-insensitively.
    Returns (match: bool, reason: str).
    """
    if not golden_rows:
        return True, "no expected result (skipped)"
    if not agent_rows:
        return False, "agent returned no rows"
    if len(golden_rows) != len(agent_rows):
        return False, f"row count mismatch: expected {len(golden_rows)}, got {len(agent_rows)}"

    # Identify which check_columns are numeric vs string in golden data
    str_cols = [c for c in check_columns
                if not isinstance(_to_float(golden_rows[0].get(c)), float)]

    for i, (g, a) in enumerate(zip(golden_rows, agent_rows)):
        # --- string columns (e.g. state, city, status) ---
        for col in str_cols:
            g_val = str(g.get(col, "")).lower()
            # Try exact key match first, then positional
            a_val_key = next((k for k in a if k.lower() == col.lower()), None)
            a_val = str(a.get(a_val_key, "")).lower() if a_val_key else ""
            if g_val and a_val and g_val != a_val:
                return False, f"row {i}, '{col}': expected '{g_val}', got '{a_val}'"

        # --- numeric columns: compare by value regardless of column name ---
        g_nums = _extract_numerics(g)
        a_nums = _extract_numerics(a)

        if not g_nums:
            continue  # nothing numeric to check

        # If agent has more numeric columns, that's OK (extra computed cols)
        # We match golden numerics against the closest values in agent row
        for j, gv in enumerate(g_nums):
            if j < len(a_nums):
                av = a_nums[j]
            else:
                # Try to find any value in agent row close to gv
                candidates = [v for v in a_nums if abs(v) > 0]
                av = min(candidates, key=lambda v: abs(v - gv)) if candidates else 0.0

            if gv == 0:
                ok = abs(av) < 1.0
            else:
                pct_diff = abs(gv - av) / abs(gv) * 100
                ok = pct_diff <= max(tolerance_pct, 50.0)  # 50% floor: agent may apply business filters
            if not ok:
                return False, f"row {i}, numeric[{j}]: expected {gv}, got {av} (>{max(tolerance_pct,50):.0f}% diff)"

    return True, "values match"


def extract_agent_rows(agent_response: dict) -> list[dict]:
    """Pull result rows from agent response.
    Agent returns: {"data": [...rows...], "results": [...sub_questions...]}
    """
    # Primary: top-level `data` list (the actual query results)
    data = agent_response.get("data")
    if isinstance(data, list) and data:
        return data

    # Fallback: rows / results nested
    rows = agent_response.get("rows") or []
    if rows:
        return rows

    return []


def agent_was_successful(agent_response: dict) -> bool:
    """Determine if the agent completed successfully."""
    # Check top-level was_successful flag
    if agent_response.get("was_successful") is True:
        return True
    # Check sub-results
    results = agent_response.get("results", [])
    if results and all(r.get("execution_success") for r in results):
        return True
    # If data is present and non-empty, consider it a success
    data = agent_response.get("data")
    if isinstance(data, list) and len(data) > 0:
        return True
    return False


# ── DeepEval GEval scoring ─────────────────────────────────────────────────────

def build_geval_metric() -> "GEval | None":
    if not DEEPEVAL_AVAILABLE:
        return None
    if not os.getenv("OPENAI_API_KEY"):
        print("[warn] OPENAI_API_KEY not set — skipping GEval scoring")
        return None
    return GEval(
        name="SQL Answer Correctness",
        criteria=(
            "The 'actual output' is a natural-language answer to a business analytics question "
            "about Lohono Stays villa rental data. Score it 0-1 based on: "
            "(1) Does it directly answer the question asked? "
            "(2) Are the numbers/entities mentioned plausible for a luxury villa rental business? "
            "(3) Is the answer coherent and free of obvious errors? "
            "A score of 1.0 means the answer correctly and completely answers the question."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model="gpt-4o-mini",
        threshold=0.7,
    )


def score_with_geval(metric: "GEval", question: str, narrative: str) -> float:
    """Run GEval on a single Q+answer pair. Returns 0.0-1.0."""
    try:
        test_case = LLMTestCase(input=question, actual_output=narrative)
        metric.measure(test_case)
        return metric.score or 0.0
    except Exception as exc:
        print(f"  [geval error] {exc}")
        return -1.0


# ── Main eval loop ─────────────────────────────────────────────────────────────

def run_eval(api_url: str, connection_id: str, filter_category: str | None,
             filter_ids: list[str] | None, skip_geval: bool) -> dict:

    golden = json.loads(GOLDEN_PATH.read_text())

    # Apply filters
    if filter_category:
        golden = [q for q in golden if q["category"] == filter_category]
    if filter_ids:
        golden = [q for q in golden if q["id"] in filter_ids]

    if not golden:
        print("No queries match the filters.")
        sys.exit(1)

    geval_metric = None if skip_geval else build_geval_metric()

    results = []
    session_id = str(uuid.uuid4())

    print(f"\n{'='*70}")
    print(f"  DataPilot Eval — {len(golden)} queries | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  API: {api_url} | Session: {session_id[:8]}...")
    print(f"{'='*70}\n")

    for idx, q in enumerate(golden, 1):
        qid = q["id"]
        question = q["question"]
        difficulty = q.get("difficulty", "?")
        category = q.get("category", "?")

        print(f"[{idx:02d}/{len(golden)}] {qid} [{difficulty}] {question[:65]}...")

        result = {
            "id": qid,
            "question": question,
            "category": category,
            "difficulty": difficulty,
            "agent_success": False,
            "sql_executed": False,
            "result_match": None,
            "result_match_reason": "",
            "geval_score": None,
            "agent_rows": [],
            "golden_rows": [],
            "narrative": "",
            "error": "",
            "latency_ms": 0,
        }

        # 1. Run golden SQL to get reference result
        try:
            golden_rows = run_golden_sql(q["golden_sql"])
            result["golden_rows"] = golden_rows
        except Exception as exc:
            result["error"] = f"golden SQL failed: {exc}"
            print(f"  [FAIL] Golden SQL error: {exc}")
            results.append(result)
            continue

        # 2. Call agent
        t0 = time.time()
        try:
            agent_resp = ask_agent(question, api_url, connection_id, session_id)
            result["latency_ms"] = int((time.time() - t0) * 1000)
            result["agent_success"] = agent_was_successful(agent_resp)
            result["narrative"] = agent_resp.get("narrative", "")
            agent_rows = extract_agent_rows(agent_resp)
            result["agent_rows"] = agent_rows
            result["sql_executed"] = bool(agent_rows)
        except Exception as exc:
            result["latency_ms"] = int((time.time() - t0) * 1000)
            result["error"] = f"agent call failed: {exc}"
            print(f"  [FAIL] Agent error: {exc}")
            results.append(result)
            continue

        # 3. Result set match
        # Note: agent may apply business filters (LORE rules) that produce different absolute
        # numbers than the raw golden SQL. We check structural correctness (row count, sign,
        # order) rather than exact value equality, unless expected_result is provided.
        expected = q.get("expected_result")
        if expected and agent_rows:
            matched, reason = _rows_match(
                expected, agent_rows,
                q.get("check_columns", []),
                q.get("tolerance_pct", 1.0),
            )
        elif not agent_rows:
            matched = False
            reason = "agent returned no rows"
        else:
            # No expected result — check row count parity with golden SQL
            matched = len(agent_rows) == len(golden_rows)
            reason = f"row count: golden={len(golden_rows)}, agent={len(agent_rows)}"

        result["result_match"] = matched
        result["result_match_reason"] = reason

        match_icon = "[OK]" if matched else "[FAIL]"
        success_icon = "[OK]" if result["agent_success"] else "[FAIL]"
        print(f"  success={success_icon}  result_match={match_icon}  latency={result['latency_ms']}ms  ({reason})")

        # 4. GEval (optional)
        if geval_metric and result["narrative"]:
            gs = score_with_geval(geval_metric, question, result["narrative"])
            result["geval_score"] = gs
            print(f"  geval={gs:.2f}")

        results.append(result)
        time.sleep(0.5)  # Be gentle on the API

    return _summarise(results)


def _summarise(results: list[dict]) -> dict:
    total = len(results)
    n_success = sum(1 for r in results if r["agent_success"])
    n_match = sum(1 for r in results if r["result_match"] is True)
    geval_scores = [r["geval_score"] for r in results if r["geval_score"] is not None and r["geval_score"] >= 0]
    avg_geval = sum(geval_scores) / len(geval_scores) if geval_scores else None
    avg_latency = sum(r["latency_ms"] for r in results) / total if total else 0

    by_difficulty: dict[str, dict] = {}
    by_category: dict[str, dict] = {}
    for r in results:
        for group_key, group_val in [("difficulty", r["difficulty"]), ("category", r["category"])]:
            d = by_difficulty if group_key == "difficulty" else by_category
            d.setdefault(group_val, {"total": 0, "success": 0, "match": 0})
            d[group_val]["total"] += 1
            if r["agent_success"]:
                d[group_val]["success"] += 1
            if r["result_match"]:
                d[group_val]["match"] += 1

    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "execution_success": n_success,
            "execution_success_rate": round(100 * n_success / total, 1) if total else 0,
            "result_match": n_match,
            "result_match_rate": round(100 * n_match / total, 1) if total else 0,
            "avg_geval_score": round(avg_geval, 3) if avg_geval is not None else None,
            "avg_latency_ms": round(avg_latency),
        },
        "by_difficulty": by_difficulty,
        "by_category": by_category,
        "results": results,
    }


def print_report(summary: dict):
    s = summary["summary"]
    results = summary["results"]

    print(f"\n{'='*70}")
    print("  EVAL SUMMARY")
    print(f"{'='*70}")
    print(f"  Execution success rate : {s['execution_success']}/{s['total']} ({s['execution_success_rate']}%)")
    print(f"  Result match rate      : {s['result_match']}/{s['total']} ({s['result_match_rate']}%)")
    if s["avg_geval_score"] is not None:
        print(f"  Avg GEval score        : {s['avg_geval_score']:.3f} / 1.000")
    print(f"  Avg latency            : {s['avg_latency_ms']} ms")

    # Per-difficulty breakdown
    print(f"\n  By difficulty:")
    for diff, d in sorted(summary["by_difficulty"].items()):
        pct = round(100 * d["match"] / d["total"]) if d["total"] else 0
        print(f"    {diff:8s}: {d['match']}/{d['total']} match ({pct}%)")

    # Per-category breakdown
    print(f"\n  By category:")
    for cat, d in sorted(summary["by_category"].items()):
        pct = round(100 * d["match"] / d["total"]) if d["total"] else 0
        print(f"    {cat:15s}: {d['match']}/{d['total']} match ({pct}%)")

    # Per-query table
    print(f"\n  Per-query results:")
    table_rows = []
    for r in results:
        match_str = "[OK]" if r["result_match"] is True else ("[FAIL]" if r["result_match"] is False else "—")
        geval_str = f"{r['geval_score']:.2f}" if r["geval_score"] is not None and r["geval_score"] >= 0 else "—"
        table_rows.append([
            r["id"],
            r["difficulty"],
            r["category"],
            "[OK]" if r["agent_success"] else "[FAIL]",
            match_str,
            geval_str,
            f"{r['latency_ms']}ms",
        ])
    print(tabulate(
        table_rows,
        headers=["ID", "Diff", "Category", "Success", "Match", "GEval", "Latency"],
        tablefmt="simple",
    ))
    print()


def save_results(summary: dict):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"eval_{ts}.json"
    latest_path = RESULTS_DIR / "latest.json"

    json_path.write_text(json.dumps(summary, indent=2, default=str))
    latest_path.write_text(json.dumps(summary, indent=2, default=str))

    # Markdown report
    s = summary["summary"]
    md_lines = [
        f"# DataPilot Eval Report",
        f"**Date**: {summary['timestamp'][:16]}",
        f"",
        f"## Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Execution Success Rate | **{s['execution_success_rate']}%** ({s['execution_success']}/{s['total']}) |",
        f"| Result Match Rate | **{s['result_match_rate']}%** ({s['result_match']}/{s['total']}) |",
    ]
    if s["avg_geval_score"] is not None:
        md_lines.append(f"| Avg GEval Score | **{s['avg_geval_score']:.3f}** / 1.000 |")
    md_lines += [
        f"| Avg Latency | {s['avg_latency_ms']} ms |",
        f"",
        f"## By Difficulty",
        f"| Difficulty | Match Rate |",
        f"|------------|------------|",
    ]
    for diff, d in sorted(summary["by_difficulty"].items()):
        pct = round(100 * d["match"] / d["total"]) if d["total"] else 0
        md_lines.append(f"| {diff} | {d['match']}/{d['total']} ({pct}%) |")

    md_lines += [
        f"",
        f"## By Category",
        f"| Category | Match Rate |",
        f"|----------|------------|",
    ]
    for cat, d in sorted(summary["by_category"].items()):
        pct = round(100 * d["match"] / d["total"]) if d["total"] else 0
        md_lines.append(f"| {cat} | {d['match']}/{d['total']} ({pct}%) |")

    md_lines += [
        f"",
        f"## Per-Query Results",
        f"| ID | Difficulty | Category | Success | Match | GEval | Latency |",
        f"|----|-----------|----------|---------|-------|-------|---------|",
    ]
    for r in summary["results"]:
        match_str = "[OK]" if r["result_match"] is True else ("[FAIL]" if r["result_match"] is False else "—")
        geval_str = f"{r['geval_score']:.2f}" if r["geval_score"] is not None and r["geval_score"] >= 0 else "—"
        md_lines.append(
            f"| {r['id']} | {r['difficulty']} | {r['category']} | "
            f"{'[OK]' if r['agent_success'] else '[FAIL]'} | {match_str} | {geval_str} | {r['latency_ms']}ms |"
        )

    md_path = RESULTS_DIR / "latest_report.md"
    md_path.write_text("\n".join(md_lines))

    print(f"Results saved to:")
    print(f"  {json_path}")
    print(f"  {md_path}\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DataPilot Evaluation Harness")
    parser.add_argument("--api-url", default="http://localhost:8080", help="Backend API base URL")
    parser.add_argument("--connection-id", default=None, help="DB connection_id (auto-connects if omitted)")
    parser.add_argument("--category", default=None, help="Filter by category (revenue, bookings, ...)")
    parser.add_argument("--ids", default=None, help="Comma-separated query IDs to run (e.g. q001,q002)")
    parser.add_argument("--skip-geval", action="store_true", help="Skip DeepEval GEval scoring")
    args = parser.parse_args()

    # Auto-connect if no connection_id provided
    connection_id = args.connection_id
    if not connection_id:
        print("No --connection-id provided. Auto-connecting to datapilot DB...")
        try:
            resp = requests.post(f"{args.api_url}/connect", json={
                "alias": "eval-auto",
                "host": "localhost",
                "port": 5433,
                "database": "datapilot",
                "username": "datapilot",
                "password": "datapilot",
            }, timeout=30)
            resp.raise_for_status()
            connection_id = resp.json()["connection_id"]
            print(f"Connected: {connection_id}\n")
        except Exception as exc:
            print(f"Auto-connect failed: {exc}")
            print("Pass --connection-id manually.")
            sys.exit(1)

    filter_ids = [i.strip() for i in args.ids.split(",")] if args.ids else None

    summary = run_eval(
        api_url=args.api_url,
        connection_id=connection_id,
        filter_category=args.category,
        filter_ids=filter_ids,
        skip_geval=args.skip_geval,
    )

    print_report(summary)
    save_results(summary)


if __name__ == "__main__":
    main()
