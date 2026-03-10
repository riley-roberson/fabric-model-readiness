"""Resurface previously deferred items so the user can revisit them."""

from __future__ import annotations

from shared.model import Disposition, ModelHistory


def get_deferred_items(history: ModelHistory) -> list[dict]:
    """Return all deferred items across sessions with context.

    Returns a list of dicts with keys: finding_id, object, category, reason, deferred_date.
    Only returns items that have not been accepted in a later session.
    """
    # Track the latest disposition per finding
    latest: dict[str, dict] = {}

    for session in history.sessions:
        for change in session.changes:
            latest[change.finding_id] = {
                "finding_id": change.finding_id,
                "object": change.object,
                "category": change.category.value,
                "action": change.action,
                "reason": change.reason,
                "session_date": str(session.timestamp),
            }

    # Filter to only deferred items
    return [
        item
        for item in latest.values()
        if item["action"] == Disposition.DEFERRED
    ]
