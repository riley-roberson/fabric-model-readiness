"""Tests for the historian append-only session logger."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from shared.model import (
    Category,
    ChangeRecord,
    ChangePlan,
    Disposition,
    ModelHistory,
)
from historian.logger import _sanitize_model_name, list_models, load_history, record_session


def _make_plan(model_name: str = "TestModel") -> ChangePlan:
    return ChangePlan(
        model_name=model_name,
        scan_id="scan-001",
        pre_score=55.0,
    )


def _make_record() -> ChangeRecord:
    return ChangeRecord(
        finding_id="f-001",
        category=Category.METADATA_COMPLETENESS,
        object="FactSales",
        action=Disposition.ACCEPTED,
        description="Added table description",
    )


# -- _sanitize_model_name ---------------------------------------------------

def test_sanitize_spaces():
    assert _sanitize_model_name("My Model") == "My_Model"


def test_sanitize_slashes():
    assert _sanitize_model_name("path/to\\model") == "path_to_model"


def test_sanitize_strips_dots():
    assert _sanitize_model_name(".model.") == "model"


# -- record_session ----------------------------------------------------------

def test_record_session_creates_file(tmp_path: Path):
    with patch("historian.logger.HISTORY_DIR", tmp_path):
        plan = _make_plan()
        records = [_make_record()]
        result = record_session(plan, records)

        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["model_name"] == "TestModel"
        assert len(data["sessions"]) == 1
        assert len(data["sessions"][0]["changes"]) == 1


def test_record_session_appends(tmp_path: Path):
    with patch("historian.logger.HISTORY_DIR", tmp_path):
        plan = _make_plan()
        record_session(plan, [_make_record()])
        record_session(plan, [_make_record()])

        path = tmp_path / "TestModel.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["sessions"]) == 2


def test_record_session_never_overwrites(tmp_path: Path):
    """Second session must preserve first session's data."""
    with patch("historian.logger.HISTORY_DIR", tmp_path):
        plan = _make_plan()
        record = _make_record()
        record_session(plan, [record])

        # Second session with a different record
        record2 = ChangeRecord(
            finding_id="f-002",
            category=Category.SCHEMA_DESIGN,
            object="DimCustomer",
            action=Disposition.DEFERRED,
            description="Deferred column rename",
        )
        record_session(plan, [record2])

        path = tmp_path / "TestModel.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["sessions"][0]["changes"][0]["finding_id"] == "f-001"
        assert data["sessions"][1]["changes"][0]["finding_id"] == "f-002"


# -- load_history ------------------------------------------------------------

def test_load_history_existing(tmp_path: Path):
    with patch("historian.logger.HISTORY_DIR", tmp_path):
        record_session(_make_plan(), [_make_record()])
        history = load_history("TestModel")
        assert history is not None
        assert history.model_name == "TestModel"
        assert len(history.sessions) == 1


def test_load_history_nonexistent(tmp_path: Path):
    with patch("historian.logger.HISTORY_DIR", tmp_path):
        history = load_history("DoesNotExist")
        assert history is None


# -- list_models -------------------------------------------------------------

def test_list_models(tmp_path: Path):
    with patch("historian.logger.HISTORY_DIR", tmp_path):
        record_session(_make_plan("ModelA"), [_make_record()])
        record_session(_make_plan("ModelB"), [_make_record()])
        models = list_models()
        assert set(models) == {"ModelA", "ModelB"}


def test_list_models_empty(tmp_path: Path):
    with patch("historian.logger.HISTORY_DIR", tmp_path):
        models = list_models()
        assert models == []
