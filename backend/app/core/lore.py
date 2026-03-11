"""
LORE — Learned Operational Rules & Evidence
Auto-updated on thumbs-up using OpenAI gpt-4o-mini.
Not injected into the pipeline yet — stored for future use.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

LORE_PATH = Path(__file__).parent.parent.parent / "knowledge" / "lore.json"

_openai_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _load() -> dict:
    try:
        return json.loads(LORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(lore: dict) -> None:
    LORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LORE_PATH.write_text(json.dumps(lore, indent=2, ensure_ascii=False), encoding="utf-8")


_SYSTEM = """You are a business intelligence analyst learning about a luxury villa rental platform called Lohono Stays.

You will receive a verified question + SQL pair. Extract any NEW business rules, SQL patterns, metric definitions, or domain knowledge NOT already present in the current LORE.

Return ONLY a JSON object with these optional keys (omit keys where nothing new was found):
{
  "verified_filters": {"key": "description or SQL fragment"},
  "metric_definitions": {"metric_name": "how it's calculated in SQL"},
  "common_joins": {"join_name": "table_a → table_b via column"},
  "business_terms": {"term": "what it means in this domain"},
  "observed_patterns": ["short description of a pattern or insight"]
}

Return {} if nothing new was found. Be concise and precise."""


def update_lore(question: str, sql: str) -> None:
    """Call gpt-4o-mini to extract business rules from a verified Q+SQL pair and merge into LORE."""
    try:
        lore = _load()
        if not lore:
            return

        current_summary = json.dumps({
            k: v for k, v in lore.items() if k != "_meta"
        }, indent=2)

        user_msg = f"""Current LORE:
{current_summary}

New verified pair:
Question: {question}
SQL:
{sql}

Extract only what is NEW and not already captured in the current LORE."""

        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=512,
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        additions = json.loads(raw)

        if not additions:
            logger.info("[LORE] No new rules extracted.")
            return

        # Merge additions into lore
        for key in ("verified_filters", "metric_definitions", "common_joins", "business_terms"):
            if key in additions and isinstance(additions[key], dict):
                lore.setdefault(key, {}).update(additions[key])

        if "observed_patterns" in additions and isinstance(additions["observed_patterns"], list):
            existing = set(lore.get("observed_patterns", []))
            for p in additions["observed_patterns"]:
                if p not in existing:
                    lore.setdefault("observed_patterns", []).append(p)

        lore["_meta"]["last_updated"] = datetime.utcnow().isoformat()
        lore["_meta"]["total_verified_queries"] = lore["_meta"].get("total_verified_queries", 0) + 1

        _save(lore)
        logger.info("[LORE] Updated with %d new sections", len(additions))

    except Exception as exc:
        logger.warning("[LORE] Update failed: %s", exc)
