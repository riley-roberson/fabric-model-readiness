"""Drift detection: compare current findings against previously accepted changes."""

from __future__ import annotations

from shared.model import (
    Category,
    Disposition,
    Finding,
    ModelHistory,
    ObjectType,
    Severity,
)


def detect_regressions(
    current_findings: list[Finding],
    history: ModelHistory,
) -> list[Finding]:
    """Find findings that match previously accepted (fixed) items -- these are regressions.

    Returns new Finding objects with elevated severity flagged as regressions.
    """
    if not history.sessions:
        return []

    # Collect all objects that were previously fixed
    previously_fixed: set[str] = set()
    for session in history.sessions:
        for change in session.changes:
            if change.action == Disposition.ACCEPTED:
                previously_fixed.add(change.object)

    regressions: list[Finding] = []
    for finding in current_findings:
        if finding.object in previously_fixed:
            regressions.append(Finding(
                category=finding.category,
                check=finding.check,
                severity=Severity.CRITICAL,  # Elevate regressions
                object=finding.object,
                object_type=finding.object_type,
                message=f"REGRESSION: {finding.message} (This was previously fixed.)",
                recommendation=finding.recommendation,
                auto_fixable=finding.auto_fixable,
            ))

    return regressions
