"""Tests for drift detection."""

from shared.model import (
    Category,
    ChangeRecord,
    Disposition,
    Finding,
    ModelHistory,
    ObjectType,
    Session,
    Severity,
)
from historian.drift import detect_regressions


def test_regression_detected():
    history = ModelHistory(
        model_name="TestModel",
        sessions=[
            Session(
                scan_id="scan-1",
                pre_score=60,
                changes=[
                    ChangeRecord(
                        finding_id="f-001",
                        category=Category.METADATA_COMPLETENESS,
                        object="FactSales",
                        action=Disposition.ACCEPTED,
                        description="Added table description",
                    )
                ],
            )
        ],
    )

    # Same object shows up again in a new scan
    current_findings = [
        Finding(
            category=Category.METADATA_COMPLETENESS,
            check="table_descriptions",
            severity=Severity.CRITICAL,
            object="FactSales",
            object_type=ObjectType.TABLE,
            message="Table 'FactSales' has no description.",
        )
    ]

    regressions = detect_regressions(current_findings, history)
    assert len(regressions) == 1
    assert "REGRESSION" in regressions[0].message
    assert regressions[0].severity == Severity.CRITICAL


def test_no_regression_for_new_findings():
    history = ModelHistory(model_name="TestModel", sessions=[])
    current_findings = [
        Finding(
            category=Category.METADATA_COMPLETENESS,
            check="table_descriptions",
            severity=Severity.CRITICAL,
            object="NewTable",
            object_type=ObjectType.TABLE,
            message="No description.",
        )
    ]
    regressions = detect_regressions(current_findings, history)
    assert len(regressions) == 0
