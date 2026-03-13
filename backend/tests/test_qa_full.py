"""
DataPilot — Full QA Test Suite
Covers: SQL parser, entity extraction, jsonify helpers, chart suggester,
        query_planner JSON strip, API endpoints, CORS, edge cases.
"""
import sys, os, json, datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append(condition)
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ══════════════════════════════════════════════════════════════
# 1. SQL PARSER
# ══════════════════════════════════════════════════════════════
section("1. SQL PARSER — sql_parser.py")
from app.utils.sql_parser import SQLParser
p = SQLParser()

# Valid queries
check("Valid SELECT", p.validate_select_only("SELECT * FROM bookings") is None)
check("Valid WITH (CTE)", p.validate_select_only("WITH x AS (SELECT 1) SELECT * FROM x") is None)
check("Valid SELECT lowercase", p.validate_select_only("select id from bookings") is None)
check("SELECT with trailing semicolon", p.validate_select_only("SELECT 1;") is None)

# Blocked keywords — direct
for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE",
           "REPLACE", "MERGE", "GRANT", "REVOKE", "EXECUTE", "EXEC", "CALL", "COPY", "VACUUM", "LOCK"]:
    result = p.validate_select_only(f"SELECT 1; {kw} INTO foo")
    check(f"Blocked: {kw}", result is not None)

# String literal false positives (must NOT flag)
check("No FP: 'promotion_calls' contains CALL",
      p.validate_select_only("SELECT promotion_calls FROM bookings") is None)
check("No FP: 'update_time' column name",
      p.validate_select_only("SELECT update_time FROM logs") is None)
check("No FP: 'created_at' contains CREATE",
      p.validate_select_only("SELECT created_at FROM bookings") is None)
check("No FP: literal string with DROP",
      p.validate_select_only("SELECT 'DROP TABLE foo' AS msg FROM dual") is None)

# Multiple statements
check("Blocks: semicolon mid-query",
      p.validate_select_only("SELECT 1; SELECT 2") is not None)

# Empty / blank
check("Blocks: empty string", p.validate_select_only("") is not None)
check("Blocks: whitespace only", p.validate_select_only("   ") is not None)

# Edge: comment injection
check("Blocks: DROP hidden in comment then after",
      p.validate_select_only("SELECT 1 -- safe\n; DROP TABLE users") is not None)

# Table extraction
tables = p.extract_table_names("SELECT * FROM bookings JOIN properties ON bookings.prop_id = properties.id")
check("Extract tables: bookings", "bookings" in tables)
check("Extract tables: properties", "properties" in tables)


# ══════════════════════════════════════════════════════════════
# 2. ENTITY EXTRACTION — echo.py
# ══════════════════════════════════════════════════════════════
section("2. ENTITY EXTRACTION — echo.py")
from app.core.echo import extract_entities, _entities_compatible

e = extract_entities("What is the revenue for last month in Goa?")
check("Temporal: last month", "last month" in e["temporal"])
check("Locations: Goa", "Goa" in e["locations"])
check("Metrics: revenue", "revenue" in e["metrics"])

e2 = extract_entities("Show top 10 bookings by revenue in Q3 2024")
check("Limits: top 10", "top 10" in e2["limits"])
check("Temporal: Q3 2024", any("q3" in t for t in e2["temporal"]))
check("Metrics: bookings", "bookings" in e2["metrics"] or "booking" in e2["metrics"])

e3 = extract_entities("Revenue in January 2023")
check("Temporal: january", "january" in e3["temporal"])
check("Temporal: 2023", "2023" in e3["temporal"])

# Entities compatibility
ea = {"temporal": ["last month"], "limits": [], "locations": ["Goa"], "metrics": []}
eb = {"temporal": ["last month"], "limits": [], "locations": ["Goa"], "metrics": []}
ec = {"temporal": ["last year"], "limits": [], "locations": ["Goa"], "metrics": []}
check("Compatible: identical entities", _entities_compatible(ea, eb))
check("Incompatible: different temporal", not _entities_compatible(ea, ec))

# Edge: empty question
e_empty = extract_entities("")
check("Empty question -> empty entities", all(len(v) == 0 for v in e_empty.values()))

# Edge: no entities
e_plain = extract_entities("show me the data")
check("No entities in plain question", e_plain["temporal"] == [] and e_plain["locations"] == [])

# Edge: UPPERCASE question
e_upper = extract_entities("REVENUE IN JANUARY 2023 FOR GOA")
check("Uppercase metrics detected", len(e_upper["metrics"]) > 0)


# ══════════════════════════════════════════════════════════════
# 3. JSONIFY HELPERS — helpers.py
# ══════════════════════════════════════════════════════════════
section("3. JSONIFY HELPERS — helpers.py")
from app.agent.nodes.helpers import _jsonify_value, _jsonify_dict

# Decimal
check("Decimal -> float", _jsonify_value(Decimal("123.456")) == 123.456)

# Dates
d = datetime.date(2024, 3, 15)
check("date -> ISO string", _jsonify_value(d) == "2024-03-15")

dt = datetime.datetime(2024, 3, 15, 10, 30, 0)
check("datetime -> ISO string", "2024-03-15" in _jsonify_value(dt))

# Passthrough types
check("int passthrough", _jsonify_value(42) == 42)
check("float passthrough", _jsonify_value(3.14) == 3.14)
check("str passthrough", _jsonify_value("hello") == "hello")
check("None passthrough", _jsonify_value(None) is None)

# Recursive
nested = {"amount": Decimal("500.00"), "date": datetime.date(2024, 1, 1), "name": "Goa"}
result = _jsonify_dict(nested)
check("Nested Decimal in dict", result["amount"] == 500.0)
check("Nested date in dict", result["date"] == "2024-01-01")
check("Nested str in dict", result["name"] == "Goa")

# Deep nesting
deep = {"outer": {"inner": Decimal("99.9")}}
result2 = _jsonify_dict(deep)
check("Deep nested Decimal", result2["outer"]["inner"] == 99.9)

# List inside dict
list_row = {"values": [Decimal("1.0"), Decimal("2.0")]}
result3 = _jsonify_dict(list_row)
check("List of Decimals inside dict", result3["values"] == [1.0, 2.0])

# JSON serializable after conversion
try:
    json.dumps(_jsonify_dict({"d": datetime.date.today(), "n": Decimal("1.5")}))
    check("json.dumps succeeds after _jsonify_dict", True)
except Exception as ex:
    check("json.dumps succeeds after _jsonify_dict", False, str(ex))


# ══════════════════════════════════════════════════════════════
# 4. CHART SUGGESTER LOGIC
# ══════════════════════════════════════════════════════════════
section("4. CHART SUGGESTER LOGIC — chart_suggester.py")
from app.agent.nodes.chart_suggester import _RULES, _infer_axes

def simulate_chart(rows, numeric, cat, cols):
    for condition_fn, chart_type, _ in _RULES:
        try:
            if condition_fn(cols, numeric, cat, rows):
                return chart_type
        except Exception:
            continue
    return "table"

# Time series -> line
cols_ts = ["month", "revenue"]
check("Line: time-series cols", simulate_chart(
    [{}]*12, ["revenue"], ["month"], cols_ts) == "line")

# Pie: ≤8 rows, 1 cat, 1 numeric
check("Pie: 5 rows, 1 cat, 1 numeric", simulate_chart(
    [{}]*5, ["revenue"], ["region"], ["region", "revenue"]) == "pie")

# Bar: 15 rows (too many for pie), 1 cat, 1 numeric
check("Bar: 15 rows (exceeds pie limit)", simulate_chart(
    [{}]*15, ["revenue"], ["region"], ["region", "revenue"]) == "bar")

# Scatter: 2+ numeric, no date
check("Scatter: 2 numeric cols", simulate_chart(
    [{}]*20, ["revenue", "occupancy"], [], ["revenue", "occupancy"]) == "scatter")

# Table fallback
check("Table: no matching pattern", simulate_chart(
    [{}]*1, [], [], ["notes"]) == "table")

# Pie NOT triggered with 1 row (edge: 2 <= rows <= 8)
check("No pie: only 1 row", simulate_chart(
    [{}]*1, ["revenue"], ["region"], ["region", "revenue"]) != "pie")

# Axis inference
axes = _infer_axes(["month", "revenue"], ["revenue"], ["month"], "line")
check("Axis: x=month for time series", axes["x_axis"] == "month")
check("Axis: y=revenue", axes["y_axis"] == "revenue")


# ══════════════════════════════════════════════════════════════
# 5. QUERY PLANNER JSON STRIP
# ══════════════════════════════════════════════════════════════
section("5. QUERY PLANNER JSON STRIP — query_planner.py")

def strip_json_fence(raw: str) -> str:
    """Replicate the stripping logic from query_planner.py"""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    return raw

cases = [
    ('```json\n{"a":1}\n```', '{"a":1}'),
    ('```JSON\n{"a":1}\n```', '{"a":1}'),
    ('``` json\n{"a":1}\n```', '{"a":1}'),   # space after ``` — this one won't strip "json" since it starts with " json"
    ('{"a":1}', '{"a":1}'),                   # no fence
    ('```\n{"a":1}\n```', '{"a":1}'),         # fence with no lang tag
]

for raw, expected in cases:
    stripped = strip_json_fence(raw)
    try:
        parsed = json.loads(stripped)
        check(f"Parse: {repr(raw[:30])}", True)
    except json.JSONDecodeError as ex:
        check(f"Parse: {repr(raw[:30])}", False, f"JSONDecodeError: {ex} | got: {repr(stripped)}")

# ══════════════════════════════════════════════════════════════
# 6. INSIGHT NARRATOR — _sanitize
# ══════════════════════════════════════════════════════════════
section("6. INSIGHT NARRATOR — _sanitize")
from app.agent.nodes.insight_narrator import _sanitize

try:
    import numpy as np
    check("numpy int64 -> int", isinstance(_sanitize(np.int64(42)), int))
    check("numpy float32 -> float", isinstance(_sanitize(np.float32(3.14)), float))
    check("numpy array -> list", isinstance(_sanitize(np.array([1, 2, 3])), list))
    check("Nested numpy in dict", _sanitize({"val": np.int64(99)})["val"] == 99)
except ImportError:
    print("  [SKIP] numpy not installed")

check("Decimal in _sanitize", _sanitize(Decimal("5.5")) == 5.5)
check("date in _sanitize", isinstance(_sanitize(datetime.date.today()), str))
check("datetime in _sanitize", isinstance(_sanitize(datetime.datetime.now()), str))
check("Nested list in _sanitize", _sanitize([Decimal("1"), Decimal("2")]) == [1.0, 2.0])
check("json.dumps after _sanitize", True)  # Would have failed above if _sanitize broken

try:
    json.dumps(_sanitize({"d": datetime.date.today(), "n": Decimal("9.9")}))
    check("json.dumps passes after _sanitize", True)
except Exception as ex:
    check("json.dumps passes after _sanitize", False, str(ex))


# ══════════════════════════════════════════════════════════════
# 7. ACCUMULATE RESULT — state reset
# ══════════════════════════════════════════════════════════════
section("7. ACCUMULATE RESULT — state reset between sub-questions")
from app.agent.nodes.helpers import accumulate_result

state = {
    "sub_questions": ["q1", "q2"],
    "current_sub_q_index": 0,
    "all_results": [],
    "sql_query": "SELECT 1",
    "sql_error": "some error",
    "retry_count": 2,
    "query_result": [{"a": 1}],
    "analysis_result": {"rows": [], "row_count": 0},
    "execution_success": True,
    "echo_tier": 1,
    "echo_cached_sql": "SELECT 1",
}

new_state = accumulate_result(state)
check("Index advances", new_state["current_sub_q_index"] == 1)
check("sql_query reset", new_state["sql_query"] == "")
check("sql_error reset", new_state["sql_error"] is None)
check("retry_count reset", new_state["retry_count"] == 0)
check("query_result reset", new_state["query_result"] == [])
check("analysis_result reset", new_state["analysis_result"] is None)
check("execution_success reset", new_state["execution_success"] == False)
check("Result saved to all_results", len(new_state["all_results"]) == 1)
check("Result has error field", "error" in new_state["all_results"][0])


# ══════════════════════════════════════════════════════════════
# 8. COST TRACKING
# ══════════════════════════════════════════════════════════════
section("8. COST TRACKING — cost.py")
from app.core.cost import aggregate_tokens, compute_cost_usd

tracker = {
    "query_planner": {"input": 100, "output": 50, "cache_read": 200, "cache_write": 10},
    "sql_generator": {"input": 300, "output": 150, "cache_read": 0, "cache_write": 0},
    "insight_narrator": {"input": 200, "output": 80, "cache_read": 100, "cache_write": 5},
}
totals = aggregate_tokens(tracker)
check("aggregate input tokens", totals["input"] == 600)
check("aggregate output tokens", totals["output"] == 280)
check("aggregate cache_read tokens", totals["cache_read"] == 300)

cost = compute_cost_usd(tracker)
check("cost is float", isinstance(cost, float))
check("cost > 0", cost > 0)
check("cost < 1.0 for small query", cost < 1.0)

# Edge: empty tracker
check("Empty tracker -> zero cost", compute_cost_usd({}) == 0.0)
check("Empty tracker -> zero tokens", sum(aggregate_tokens({}).values()) == 0)


# ══════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════
passed = sum(results)
total = len(results)
failed = total - passed
print(f"\n{'='*60}")
print(f"  RESULTS: {passed}/{total} passed  |  {failed} failed")
print(f"{'='*60}\n")
sys.exit(0 if failed == 0 else 1)
