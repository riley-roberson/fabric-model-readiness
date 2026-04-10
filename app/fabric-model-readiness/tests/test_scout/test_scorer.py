"""Tests for the readiness score computation."""

from shared.model import Category, Finding, ObjectType, Severity
from scout.scorer import compute_summary, rating


def _finding(category: Category, severity: Severity) -> Finding:
    return Finding(
        category=category,
        check="test_check",
        severity=severity,
        object="TestObj",
        object_type=ObjectType.TABLE,
        message="test",
    )


# -- compute_summary ---------------------------------------------------------

def test_no_findings_perfect_score():
    summary = compute_summary([], {"schema_design": 10, "metadata_completeness": 5})
    assert summary.score == 100.0


def test_all_failures_zero_score():
    findings = [_finding(Category.SCHEMA_DESIGN, Severity.HIGH) for _ in range(10)]
    summary = compute_summary(findings, {"schema_design": 10})
    assert summary.score == 0.0


def test_critical_penalty_doubles():
    """A CRITICAL finding counts as 2 failures, so 1 CRITICAL in 10 checks = 8/10."""
    findings = [_finding(Category.SCHEMA_DESIGN, Severity.CRITICAL)]
    summary = compute_summary(findings, {"schema_design": 10})
    # With CRITICAL_PENALTY_MULTIPLIER=2: (10-2)/10 = 0.8 -> 80.0
    assert summary.score == 80.0


def test_high_finding_counts_as_one():
    findings = [_finding(Category.SCHEMA_DESIGN, Severity.HIGH)]
    summary = compute_summary(findings, {"schema_design": 10})
    # 1 HIGH: (10-1)/10 = 0.9 -> 90.0
    assert summary.score == 90.0


def test_weighted_across_categories():
    """Multiple categories contribute proportionally to their weights."""
    findings = [
        _finding(Category.AI_PREPARATION, Severity.HIGH),  # 1 fail in ai_prep
    ]
    total_checks = {
        "ai_preparation": 10,      # 9/10 = 0.9, weight=0.20
        "metadata_completeness": 5, # 5/5 = 1.0, weight=0.20
    }
    summary = compute_summary(findings, total_checks)
    # weighted = (0.9*0.20 + 1.0*0.20) / (0.20+0.20) = 0.38/0.40 = 0.95 -> 95.0
    assert summary.score == 95.0


def test_empty_category_excluded():
    """Categories with 0 total checks don't affect the score."""
    findings = []
    total_checks = {"schema_design": 5, "metadata_completeness": 0}
    summary = compute_summary(findings, total_checks)
    assert summary.score == 100.0


def test_no_checks_at_all_zero_score():
    summary = compute_summary([], {})
    assert summary.score == 0.0


def test_severity_counts():
    findings = [
        _finding(Category.SCHEMA_DESIGN, Severity.CRITICAL),
        _finding(Category.SCHEMA_DESIGN, Severity.HIGH),
        _finding(Category.SCHEMA_DESIGN, Severity.HIGH),
        _finding(Category.SCHEMA_DESIGN, Severity.MEDIUM),
        _finding(Category.SCHEMA_DESIGN, Severity.LOW),
        _finding(Category.SCHEMA_DESIGN, Severity.INFO),
    ]
    summary = compute_summary(findings, {"schema_design": 100})
    assert summary.critical == 1
    assert summary.high == 2
    assert summary.medium == 1
    assert summary.low == 1
    assert summary.info == 1


# -- rating ------------------------------------------------------------------

def test_rating_ai_ready():
    assert rating(100.0) == "AI-Ready"
    assert rating(90.0) == "AI-Ready"


def test_rating_mostly_ready():
    assert rating(89.9) == "Mostly Ready (minor gaps)"
    assert rating(75.0) == "Mostly Ready (minor gaps)"


def test_rating_needs_work():
    assert rating(74.9) == "Needs Work (significant gaps)"
    assert rating(50.0) == "Needs Work (significant gaps)"


def test_rating_not_ready():
    assert rating(49.9) == "Not Ready (fundamental issues)"
    assert rating(0.0) == "Not Ready (fundamental issues)"
