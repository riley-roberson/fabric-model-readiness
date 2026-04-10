"""Computes the 0-100 readiness score from a list of findings."""

from __future__ import annotations

from shared.config import CATEGORY_WEIGHTS, CRITICAL_PENALTY_MULTIPLIER
from shared.model import Finding, ScanSummary, Severity


def compute_summary(findings: list[Finding], total_checks_by_category: dict[str, int]) -> ScanSummary:
    """Compute severity counts and weighted readiness score.

    Args:
        findings: All findings from the rule engine.
        total_checks_by_category: Total checks run per category key
            (e.g. {"schema_design": 15, "metadata_completeness": 42, ...}).
            If a category had zero checks, it is excluded from scoring.
    """
    summary = ScanSummary()

    # Count by severity
    for f in findings:
        match f.severity:
            case Severity.CRITICAL:
                summary.critical += 1
            case Severity.HIGH:
                summary.high += 1
            case Severity.MEDIUM:
                summary.medium += 1
            case Severity.LOW:
                summary.low += 1
            case Severity.INFO:
                summary.info += 1

    # Weighted score
    failures_by_cat: dict[str, int] = {}
    for f in findings:
        cat = f.category.value
        penalty = CRITICAL_PENALTY_MULTIPLIER if f.severity == Severity.CRITICAL else 1
        failures_by_cat[cat] = failures_by_cat.get(cat, 0) + penalty

    weighted_score = 0.0
    total_weight = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        total = total_checks_by_category.get(cat, 0)
        if total == 0:
            continue
        failed = failures_by_cat.get(cat, 0)
        passing = max(0, total - failed)
        cat_score = passing / total
        weighted_score += cat_score * weight
        total_weight += weight

    if total_weight > 0:
        summary.score = round((weighted_score / total_weight) * 100, 1)
    else:
        summary.score = 0.0

    return summary


def rating(score: float) -> str:
    """Return a human-readable rating string."""
    if score >= 90:
        return "AI-Ready"
    elif score >= 75:
        return "Mostly Ready (minor gaps)"
    elif score >= 50:
        return "Needs Work (significant gaps)"
    else:
        return "Not Ready (fundamental issues)"
