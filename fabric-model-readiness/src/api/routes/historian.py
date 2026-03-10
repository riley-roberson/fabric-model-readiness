"""Historian API route: GET /api/history for change history retrieval."""

from __future__ import annotations

import json
import re
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from historian.logger import list_models, load_history
from shared.config import HISTORY_DIR

router = APIRouter(prefix="/api", tags=["historian"])


def _sanitize_model_name(name: str) -> str:
    """Sanitize a model name for use as a filename (matches historian logger)."""
    return name.replace("/", "_").replace("\\", "_").replace(" ", "_").strip("._")


def _sanitize_aggressive(name: str) -> str:
    """Strip all non-alphanumeric chars except underscores (matches Historian skill convention)."""
    result = re.sub(r"[^a-zA-Z0-9_]", "", _sanitize_model_name(name))
    result = re.sub(r"_+", "_", result)  # collapse consecutive underscores
    return result.strip("_")


def _find_history_file(model_name: str):
    """Find the history JSON file, trying multiple strategies."""
    # Strategy 1: exact sanitize (logger.py convention)
    path = HISTORY_DIR / f"{_sanitize_model_name(model_name)}.json"
    if path.exists():
        return path

    # Strategy 2: aggressive sanitize (strips +, &, etc. -- Historian skill convention)
    path = HISTORY_DIR / f"{_sanitize_aggressive(model_name)}.json"
    if path.exists():
        return path

    # Strategy 3: case-insensitive match on file stem
    target = _sanitize_aggressive(model_name).lower()
    for candidate in HISTORY_DIR.glob("*.json"):
        if candidate.stem.lower() == target:
            return candidate

    # Strategy 4: substring match (handles "Big_Bulky_Co" matching "Big_Bulky_Co_Model")
    for candidate in HISTORY_DIR.glob("*.json"):
        stem = candidate.stem.lower()
        if target in stem or stem in target:
            return candidate

    # Strategy 5: match on modelName field inside the JSON files
    for candidate in HISTORY_DIR.glob("*.json"):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            stored_name = data.get("modelName", data.get("model_name", ""))
            if _sanitize_aggressive(stored_name).lower() == target:
                return candidate
            # Also try if the input contains the stored name or vice versa
            stored_lower = _sanitize_aggressive(stored_name).lower()
            if target in stored_lower or stored_lower in target:
                return candidate
        except (json.JSONDecodeError, OSError):
            continue

    return None


def _load_raw_history(model_name: str) -> dict | None:
    """Load raw JSON history (handles camelCase from Historian skill)."""
    path = _find_history_file(model_name)
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _compute_session_summary(session: dict) -> dict:
    """Compute category-level and action-level summaries for a session."""
    changes = session.get("changes", [])

    by_category: dict[str, dict[str, int]] = defaultdict(
        lambda: {"accepted": 0, "deferred": 0, "rejected": 0}
    )
    by_action = {"accepted": 0, "deferred": 0, "rejected": 0}

    for change in changes:
        action = change.get("action", "")
        category = change.get("category", "unknown")
        if action in by_action:
            by_action[action] += 1
            by_category[category][action] += 1

    # Include appliedSummary if present in the raw data
    applied_summary = session.get("appliedSummary")

    return {
        "byCategory": dict(by_category),
        "byAction": by_action,
        "appliedSummary": applied_summary,
    }


def _get_deferred_items_from_raw(raw: dict) -> list[dict]:
    """Extract outstanding deferred items from raw history JSON."""
    latest: dict[str, dict] = {}
    for session in raw.get("sessions", []):
        session_date = session.get("timestamp", "")
        for change in session.get("changes", []):
            finding_id = change.get("findingId", change.get("finding_id", ""))
            latest[finding_id] = {
                "findingId": finding_id,
                "object": change.get("object", ""),
                "category": change.get("category", ""),
                "action": change.get("action", ""),
                "reason": change.get("reason"),
                "description": change.get("description", ""),
                "sessionDate": session_date,
            }
    return [item for item in latest.values() if item["action"] == "deferred"]


@router.get("/history")
async def get_history(model: str | None = None):
    """Return change history. If model is specified, return that model's history. Otherwise list all."""
    if model:
        return await get_model_history_enriched(model)

    models = list_models()
    return {"models": models}


@router.get("/history/{model_name}")
async def get_model_history_enriched(model_name: str):
    """Return enriched history for a model with session summaries."""
    raw = _load_raw_history(model_name)
    if raw is None:
        # Fall back to Pydantic-based loader (handles snake_case files)
        history = load_history(model_name)
        if history is None:
            raise HTTPException(
                status_code=404, detail=f"No history found for model: {model_name}"
            )
        raw = json.loads(history.model_dump_json())

    # Enrich each session with computed summaries
    for session in raw.get("sessions", []):
        session["sessionSummary"] = _compute_session_summary(session)

    # Add outstanding deferred items
    raw["deferredItems"] = _get_deferred_items_from_raw(raw)

    return raw


@router.get("/history/{model_name}/deferred")
async def get_deferred_items(model_name: str):
    """Return outstanding deferred items for a model."""
    raw = _load_raw_history(model_name)
    if raw is None:
        history = load_history(model_name)
        if history is None:
            raise HTTPException(
                status_code=404, detail=f"No history found for model: {model_name}"
            )
        raw = json.loads(history.model_dump_json())

    return {"modelName": model_name, "items": _get_deferred_items_from_raw(raw)}
