"""
DataPilot — Cost calculator for Anthropic Claude API calls.
Prices are for claude-sonnet-4-5 as of early 2026.
"""

# USD per million tokens
COST_PER_MTOK = {
    "input": 3.00,
    "output": 15.00,
    "cache_write": 3.75,   # cache_creation_input_tokens
    "cache_read": 0.30,    # cache_read_input_tokens (90% cheaper than input)
}


def compute_cost_usd(tracker: dict) -> float:
    """
    Compute total cost from a token_tracker dict.
    tracker shape: {node_name: {input, output, cache_write, cache_read}}
    """
    totals = aggregate_tokens(tracker)
    return sum(totals[k] * COST_PER_MTOK[k] / 1_000_000 for k in COST_PER_MTOK)


def aggregate_tokens(tracker: dict) -> dict:
    """Sum all token counts across nodes. Returns {input, output, cache_write, cache_read}."""
    totals = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    for node_usage in tracker.values():
        if isinstance(node_usage, dict):
            for k in totals:
                totals[k] += node_usage.get(k, 0)
    return totals
