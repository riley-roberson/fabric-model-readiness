"""Append-only session logger. Records every Enforcer session to .history/[model].json."""

from __future__ import annotations

import json
from pathlib import Path

from shared.config import HISTORY_DIR
from shared.model import ChangeRecord, ChangePlan, ModelHistory, Session


def record_session(plan: ChangePlan, records: list[ChangeRecord]) -> Path:
    """Append a new session to the model's history file. Never overwrites existing data."""
    model_name = _sanitize_model_name(plan.model_name)
    history_path = HISTORY_DIR / f"{model_name}.json"

    # Load existing history or create new
    if history_path.exists():
        data = json.loads(history_path.read_text(encoding="utf-8"))
        history = ModelHistory(**data)
    else:
        history = ModelHistory(model_name=model_name)

    session = Session(
        scan_id=plan.scan_id,
        pre_score=plan.pre_score,
        post_score=None,  # Will be set after a re-scan
        changes=records,
    )

    history.sessions.append(session)

    history_path.write_text(
        json.dumps(history.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8",
    )

    return history_path


def load_history(model_name: str) -> ModelHistory | None:
    """Load the full history for a model."""
    sanitized = _sanitize_model_name(model_name)
    history_path = HISTORY_DIR / f"{sanitized}.json"
    if not history_path.exists():
        return None
    data = json.loads(history_path.read_text(encoding="utf-8"))
    return ModelHistory(**data)


def list_models() -> list[str]:
    """Return names of all models that have history."""
    return [p.stem for p in HISTORY_DIR.glob("*.json")]


def _sanitize_model_name(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").replace(" ", "_").strip("._")
