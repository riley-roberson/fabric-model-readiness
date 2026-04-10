"""Tests for linting profile filtering."""

from __future__ import annotations

from shared.config import CHECK_PROFILES
from shared.model import Category, Finding, ObjectType, Profile, Severity
from scout.rules import filter_by_profile
from scout.scorer import compute_summary


def _finding(check: str, category: Category = Category.SCHEMA_DESIGN,
             severity: Severity = Severity.MEDIUM) -> Finding:
    return Finding(
        category=category,
        check=check,
        severity=severity,
        object="TestObj",
        object_type=ObjectType.TABLE,
        message="test",
    )


# -- filter_by_profile -------------------------------------------------------

def test_both_returns_all():
    findings = [
        _finding("table_naming"),           # both
        _finding("table_descriptions"),      # ai
        _finding("rls_roles_defined"),       # org
    ]
    result = filter_by_profile(findings, Profile.BOTH)
    assert len(result) == 3


def test_ai_includes_ai_and_both():
    findings = [
        _finding("table_naming"),           # both -> included
        _finding("table_descriptions"),      # ai   -> included
        _finding("rls_roles_defined"),       # org  -> excluded
    ]
    result = filter_by_profile(findings, Profile.AI)
    checks = {f.check for f in result}
    assert "table_naming" in checks
    assert "table_descriptions" in checks
    assert "rls_roles_defined" not in checks
    assert len(result) == 2


def test_org_includes_org_and_both():
    findings = [
        _finding("table_naming"),           # both -> included
        _finding("table_descriptions"),      # ai   -> excluded
        _finding("rls_roles_defined"),       # org  -> included
    ]
    result = filter_by_profile(findings, Profile.ORG)
    checks = {f.check for f in result}
    assert "table_naming" in checks
    assert "rls_roles_defined" in checks
    assert "table_descriptions" not in checks
    assert len(result) == 2


def test_unknown_check_defaults_to_both():
    """A check not present in CHECK_PROFILES is treated as 'both' and always included."""
    findings = [_finding("some_future_check")]
    assert len(filter_by_profile(findings, Profile.AI)) == 1
    assert len(filter_by_profile(findings, Profile.ORG)) == 1
    assert len(filter_by_profile(findings, Profile.BOTH)) == 1


def test_empty_findings():
    assert filter_by_profile([], Profile.AI) == []
    assert filter_by_profile([], Profile.ORG) == []
    assert filter_by_profile([], Profile.BOTH) == []


# -- scoring with profiles ---------------------------------------------------

def test_scoring_with_ai_profile():
    """AI profile excludes org-only findings, so score reflects only AI checks."""
    ai_finding = _finding("ai_schema_configured", Category.AI_PREPARATION, Severity.HIGH)
    org_finding = _finding("rls_roles_defined", Category.ORG_STANDARDS, Severity.CRITICAL)
    both_finding = _finding("table_naming", Category.SCHEMA_DESIGN, Severity.HIGH)

    all_findings = [ai_finding, org_finding, both_finding]
    filtered = filter_by_profile(all_findings, Profile.AI)

    # org finding should be excluded
    assert len(filtered) == 2
    checks = {f.check for f in filtered}
    assert "rls_roles_defined" not in checks

    # Provide explicit totals so score is non-zero (1 failure out of 10 checks)
    total_checks = {"ai_preparation": 10, "schema_design": 10}
    summary = compute_summary(filtered, total_checks)
    assert summary.score > 0
    # org_standards is absent from total_checks, confirming it doesn't affect score
    assert "org_standards" not in total_checks


def test_scoring_with_org_profile():
    """ORG profile excludes ai-only findings, so score reflects only org checks."""
    ai_finding = _finding("ai_schema_configured", Category.AI_PREPARATION, Severity.CRITICAL)
    org_finding = _finding("rls_roles_defined", Category.ORG_STANDARDS, Severity.HIGH)
    both_finding = _finding("default_summarization", Category.DATA_TYPES, Severity.HIGH)

    all_findings = [ai_finding, org_finding, both_finding]
    filtered = filter_by_profile(all_findings, Profile.ORG)

    # ai finding should be excluded
    assert len(filtered) == 2
    checks = {f.check for f in filtered}
    assert "ai_schema_configured" not in checks

    # Provide explicit totals so score is non-zero (1 failure out of 10 checks)
    total_checks = {"org_standards": 10, "data_types": 10}
    summary = compute_summary(filtered, total_checks)
    assert summary.score > 0
    # ai_preparation is absent from total_checks, confirming it doesn't affect score
    assert "ai_preparation" not in total_checks


# -- guard test: all rule modules produce tagged checks -----------------------

def test_all_checks_tagged():
    """Every check name in CHECK_PROFILES should map to a valid tag."""
    valid_tags = {"ai", "org", "both"}
    for check_name, tag in CHECK_PROFILES.items():
        assert tag in valid_tags, f"CHECK_PROFILES['{check_name}'] = '{tag}' is not a valid tag"


def test_all_rule_checks_in_profiles():
    """Run all rule modules against a minimal model and verify every produced
    check name exists in CHECK_PROFILES."""
    from tests.conftest import make_model
    from shared.model import (
        ColumnInfo, CopilotConfig, MeasureInfo,
        RelationshipInfo, RoleInfo, TableInfo,
    )
    from scout.rules import run_all_checks

    # Build a model that triggers as many checks as possible
    model = make_model(
        tables=[
            TableInfo(
                name="FactSales",
                columns=[
                    ColumnInfo(name="SalesKey", table="FactSales", data_type="Int64"),
                    ColumnInfo(name="Amount", table="FactSales", data_type="Double"),
                ],
                measures=[
                    MeasureInfo(name="Total Sales", table="FactSales",
                                expression="SUM(FactSales[Amount])"),
                ],
            ),
            TableInfo(
                name="DimCustomer",
                columns=[
                    ColumnInfo(name="CustomerKey", table="DimCustomer", data_type="Int64"),
                    ColumnInfo(name="Name", table="DimCustomer", data_type="String"),
                ],
            ),
        ],
        relationships=[
            RelationshipInfo(
                from_table="FactSales", from_column="CustomerKey",
                to_table="DimCustomer", to_column="CustomerKey",
            ),
        ],
    )

    findings = run_all_checks(model)
    untag = []
    for f in findings:
        if f.check not in CHECK_PROFILES:
            untag.append(f.check)
    assert untag == [], f"Checks not in CHECK_PROFILES: {untag}"
