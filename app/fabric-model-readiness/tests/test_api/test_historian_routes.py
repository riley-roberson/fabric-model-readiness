"""Tests for the historian API routes."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.server import app
from api.routes.historian import (
    _compute_session_summary,
    _get_deferred_items_from_raw,
    _sanitize_aggressive,
    _sanitize_model_name,
)

client = TestClient(app)


# -- Health endpoint ---------------------------------------------------------

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# -- Sanitization helpers ----------------------------------------------------

def test_sanitize_model_name_spaces():
    assert _sanitize_model_name("Big Bulky Co") == "Big_Bulky_Co"


def test_sanitize_aggressive_special_chars():
    assert _sanitize_aggressive("Big + Bulky Co.SemanticModel") == "Big_Bulky_CoSemanticModel"


def test_sanitize_aggressive_collapses_underscores():
    assert _sanitize_aggressive("Big + + Bulky") == "Big_Bulky"


# -- _compute_session_summary -----------------------------------------------

def test_compute_session_summary_counts():
    session = {
        "changes": [
            {"action": "accepted", "category": "schema_design"},
            {"action": "accepted", "category": "schema_design"},
            {"action": "deferred", "category": "metadata_completeness"},
            {"action": "rejected", "category": "schema_design"},
        ],
    }
    summary = _compute_session_summary(session)
    assert summary["byAction"]["accepted"] == 2
    assert summary["byAction"]["deferred"] == 1
    assert summary["byAction"]["rejected"] == 1
    assert summary["byCategory"]["schema_design"]["accepted"] == 2
    assert summary["byCategory"]["metadata_completeness"]["deferred"] == 1


def test_compute_session_summary_empty():
    summary = _compute_session_summary({"changes": []})
    assert summary["byAction"] == {"accepted": 0, "deferred": 0, "rejected": 0}
    assert summary["byCategory"] == {}


def test_compute_session_summary_includes_applied():
    session = {
        "changes": [],
        "appliedSummary": {"appliedViaMCP": 5, "skippedMCPUnsupported": 2},
    }
    summary = _compute_session_summary(session)
    assert summary["appliedSummary"]["appliedViaMCP"] == 5


# -- _get_deferred_items_from_raw --------------------------------------------

def test_deferred_items_from_raw():
    raw = {
        "sessions": [{
            "timestamp": "2026-01-01",
            "changes": [
                {"findingId": "f-001", "action": "deferred", "object": "A", "category": "schema_design"},
                {"findingId": "f-002", "action": "accepted", "object": "B", "category": "metadata"},
            ],
        }],
    }
    items = _get_deferred_items_from_raw(raw)
    assert len(items) == 1
    assert items[0]["findingId"] == "f-001"


def test_deferred_then_accepted_excluded():
    raw = {
        "sessions": [
            {"timestamp": "2026-01-01", "changes": [
                {"findingId": "f-001", "action": "deferred", "object": "A", "category": "c"},
            ]},
            {"timestamp": "2026-02-01", "changes": [
                {"findingId": "f-001", "action": "accepted", "object": "A", "category": "c"},
            ]},
        ],
    }
    items = _get_deferred_items_from_raw(raw)
    assert len(items) == 0


# -- GET /api/history --------------------------------------------------------

def test_get_history_lists_models(tmp_path: Path):
    """When no model is specified, return the model listing."""
    # Create a fake history file
    history_data = {"model_name": "TestModel", "sessions": []}
    (tmp_path / "TestModel.json").write_text(json.dumps(history_data), encoding="utf-8")

    with patch("api.routes.historian.HISTORY_DIR", tmp_path), \
         patch("historian.logger.HISTORY_DIR", tmp_path):
        response = client.get("/api/history")
        assert response.status_code == 200
        assert "TestModel" in response.json()["models"]


# -- GET /api/history/{model_name} -------------------------------------------

def test_get_model_history_enriched(tmp_path: Path):
    history_data = {
        "model_name": "TestModel",
        "sessions": [{
            "session_id": "s1",
            "timestamp": "2026-01-01",
            "scan_id": "scan1",
            "pre_score": 55,
            "changes": [
                {"findingId": "f-001", "action": "accepted", "object": "A", "category": "schema_design", "description": "d"},
                {"findingId": "f-002", "action": "deferred", "object": "B", "category": "metadata", "description": "d"},
            ],
        }],
    }
    (tmp_path / "TestModel.json").write_text(json.dumps(history_data), encoding="utf-8")

    with patch("api.routes.historian.HISTORY_DIR", tmp_path), \
         patch("historian.logger.HISTORY_DIR", tmp_path):
        response = client.get("/api/history/TestModel")
        assert response.status_code == 200
        data = response.json()
        # Should have enriched session summary
        assert "sessionSummary" in data["sessions"][0]
        assert data["sessions"][0]["sessionSummary"]["byAction"]["accepted"] == 1
        # Should have deferred items
        assert len(data["deferredItems"]) == 1


def test_get_model_history_404(tmp_path: Path):
    with patch("api.routes.historian.HISTORY_DIR", tmp_path), \
         patch("historian.logger.HISTORY_DIR", tmp_path):
        response = client.get("/api/history/NonExistent")
        assert response.status_code == 404


# -- GET /api/history/{model_name}/deferred ----------------------------------

def test_get_deferred_items_endpoint(tmp_path: Path):
    history_data = {
        "model_name": "TestModel",
        "sessions": [{
            "timestamp": "2026-01-01",
            "changes": [
                {"findingId": "f-001", "action": "deferred", "object": "A", "category": "c", "description": "d"},
            ],
        }],
    }
    (tmp_path / "TestModel.json").write_text(json.dumps(history_data), encoding="utf-8")

    with patch("api.routes.historian.HISTORY_DIR", tmp_path), \
         patch("historian.logger.HISTORY_DIR", tmp_path):
        response = client.get("/api/history/TestModel/deferred")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["findingId"] == "f-001"
