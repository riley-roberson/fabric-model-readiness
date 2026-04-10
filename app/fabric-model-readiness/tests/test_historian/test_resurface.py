"""Tests for deferred item resurfacing."""

from shared.model import (
    Category,
    ChangeRecord,
    Disposition,
    ModelHistory,
    Session,
)
from historian.resurface import get_deferred_items


def test_get_deferred_items_returns_deferred():
    history = ModelHistory(
        model_name="Test",
        sessions=[Session(
            scan_id="s1",
            pre_score=50,
            changes=[
                ChangeRecord(
                    finding_id="f-001",
                    category=Category.METADATA_COMPLETENESS,
                    object="FactSales",
                    action=Disposition.DEFERRED,
                    description="Deferred",
                    reason="Need more context",
                ),
                ChangeRecord(
                    finding_id="f-002",
                    category=Category.SCHEMA_DESIGN,
                    object="DimProduct",
                    action=Disposition.ACCEPTED,
                    description="Accepted",
                ),
            ],
        )],
    )
    items = get_deferred_items(history)
    assert len(items) == 1
    assert items[0]["finding_id"] == "f-001"
    assert items[0]["reason"] == "Need more context"


def test_get_deferred_items_empty_history():
    history = ModelHistory(model_name="Test", sessions=[])
    items = get_deferred_items(history)
    assert items == []


def test_deferred_then_accepted_not_returned():
    """If an item is deferred in session 1 but accepted in session 2, it should not appear."""
    history = ModelHistory(
        model_name="Test",
        sessions=[
            Session(
                scan_id="s1",
                pre_score=50,
                changes=[ChangeRecord(
                    finding_id="f-001",
                    category=Category.METADATA_COMPLETENESS,
                    object="FactSales",
                    action=Disposition.DEFERRED,
                    description="Deferred initially",
                )],
            ),
            Session(
                scan_id="s2",
                pre_score=60,
                changes=[ChangeRecord(
                    finding_id="f-001",
                    category=Category.METADATA_COMPLETENESS,
                    object="FactSales",
                    action=Disposition.ACCEPTED,
                    description="Accepted later",
                )],
            ),
        ],
    )
    items = get_deferred_items(history)
    assert len(items) == 0


def test_multiple_deferred_items():
    history = ModelHistory(
        model_name="Test",
        sessions=[Session(
            scan_id="s1",
            pre_score=50,
            changes=[
                ChangeRecord(
                    finding_id="f-001",
                    category=Category.METADATA_COMPLETENESS,
                    object="A",
                    action=Disposition.DEFERRED,
                    description="D1",
                ),
                ChangeRecord(
                    finding_id="f-002",
                    category=Category.SCHEMA_DESIGN,
                    object="B",
                    action=Disposition.DEFERRED,
                    description="D2",
                ),
                ChangeRecord(
                    finding_id="f-003",
                    category=Category.RELATIONSHIPS,
                    object="C",
                    action=Disposition.REJECTED,
                    description="R1",
                ),
            ],
        )],
    )
    items = get_deferred_items(history)
    assert len(items) == 2
    ids = {item["finding_id"] for item in items}
    assert ids == {"f-001", "f-002"}
