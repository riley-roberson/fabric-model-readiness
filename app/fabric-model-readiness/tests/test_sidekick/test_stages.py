"""Phase-aware linting: nothing orphaned, nothing surfacing too early."""

from __future__ import annotations

import pytest

from shared.config import CHECK_PROFILES
from shared.model import Category, Finding, ObjectType, Severity
from sidekick.process import load_process
from sidekick.stages import (
    CHECK_STAGES,
    active_checks,
    filter_by_stage,
    stage_of,
    stage_progress,
)


def _finding(check: str) -> Finding:
    return Finding(
        category=Category.SCHEMA_DESIGN,
        check=check,
        severity=Severity.MEDIUM,
        object="X",
        object_type=ObjectType.TABLE,
        message="",
    )


def test_every_check_is_staged():
    """An unstaged check silently falls back to the default stage.

    That is a safe default but a poor one to rely on: it means a new check
    appears at model development whether or not that is where it belongs.
    """
    missing = set(CHECK_PROFILES) - set(CHECK_STAGES)
    assert not missing, f"checks with no stage assignment: {sorted(missing)}"


def test_no_stage_assignments_for_checks_that_do_not_exist():
    orphans = set(CHECK_STAGES) - set(CHECK_PROFILES)
    assert not orphans, f"staged checks that are not registered: {sorted(orphans)}"


def test_stages_referenced_are_real():
    stage_ids = {s.id for s in load_process().stages}
    unknown = {s for s in CHECK_STAGES.values() if s not in stage_ids}
    assert not unknown, f"unknown stages referenced: {sorted(unknown)}"


def test_nothing_is_checkable_before_a_model_exists():
    """Scout parses the .SemanticModel folder, which does not exist during the
    warehouse stages. Reporting anything there would be reporting on nothing.
    """
    for stage in ("project_launch", "requirements_design", "bronze", "silver", "gold"):
        assert active_checks(stage) == set(), f"{stage} should have no active checks"


def test_model_development_activates_the_structural_checks():
    active = active_checks("pbi_development")
    assert "star_schema_structure" in active
    assert "default_summarization" in active
    assert "rls_roles_defined" in active
    # Data Agent concerns are not yet in play.
    assert "verified_answers" not in active
    assert "ai_instructions_present" not in active


def test_ai_readiness_activates_everything():
    active = active_checks("ai_readiness")
    assert active == set(CHECK_PROFILES), "by AI readiness every check should be live"


def test_later_stages_never_lose_checks():
    """Checks accumulate: a stage always includes everything earlier stages had."""
    process = load_process()
    seen: set[str] = set()
    for stage in process.stages:
        active = active_checks(stage.id)
        assert seen <= active, f"{stage.id} dropped checks that were already active"
        seen = active


def test_filter_suppresses_rather_than_reorders():
    findings = [_finding("star_schema_structure"), _finding("verified_answers")]
    filtered = filter_by_stage(findings, "pbi_development")
    assert [f.check for f in filtered] == ["star_schema_structure"]


def test_progress_is_scored_against_what_is_in_play():
    """The whole point: a clean model mid-build should not read as a failure."""
    findings = [_finding("star_schema_structure"), _finding("verified_answers")]

    at_dev = stage_progress(findings, "pbi_development")
    assert at_dev["checks_failing"] == 1
    assert at_dev["suppressed"] == 1
    assert at_dev["checks_in_play"] == len(active_checks("pbi_development"))

    at_ai = stage_progress(findings, "ai_readiness")
    assert at_ai["checks_failing"] == 2
    assert at_ai["suppressed"] == 0
    assert at_ai["checks_in_play"] == len(CHECK_PROFILES)


def test_a_clean_model_scores_100_at_its_stage():
    assert stage_progress([], "pbi_development")["percent"] == 100


@pytest.mark.parametrize("check", ["table_descriptions", "synonyms", "row_label_defined"])
def test_documentation_checks_wait_for_ai_readiness(check):
    """Demanding descriptions mid-build buries everything else."""
    assert stage_of(check) == "ai_readiness"
