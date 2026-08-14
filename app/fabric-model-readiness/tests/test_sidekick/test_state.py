"""Project state, persistence, and the one rule that does not bend."""

from __future__ import annotations

import json

import pytest

from sidekick.process import load_process
from sidekick.state import (
    ProjectState,
    load_state,
    save_state,
    start_project,
    state_path,
)


@pytest.fixture
def project(tmp_path):
    return start_project(tmp_path, name="Donations", size="medium")


def test_state_lives_at_the_project_root_not_in_the_model(tmp_path, project):
    """The first five stages are warehouse work, before any model exists."""
    assert state_path(tmp_path).name == "sidekick.json"
    assert state_path(tmp_path).parent == tmp_path.resolve()


def test_new_project_starts_at_the_first_stage(project):
    assert project.current_stage == load_process().stages[0].id
    assert project.overall_completion()["resolved"] == 0


def test_round_trips_through_disk(tmp_path, project):
    project.mark_step("assign_roles", "done", note="Riley modelling")
    save_state(project)

    reloaded = load_state(tmp_path)
    assert reloaded is not None
    assert reloaded.step_state("assign_roles").state == "done"
    assert reloaded.step_state("assign_roles").note == "Riley modelling"


def test_missing_state_is_not_an_error(tmp_path):
    assert load_state(tmp_path) is None


def test_unreadable_state_is_reported_clearly(tmp_path):
    state_path(tmp_path).write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not readable Sidekick state"):
        load_state(tmp_path)


def test_save_is_atomic(tmp_path, project):
    """A half-written state file would lose the project's whole history."""
    save_state(project)
    assert not list(tmp_path.glob("*.tmp"))
    json.loads(state_path(tmp_path).read_text(encoding="utf-8"))


def test_skipping_requires_a_reason(project):
    """The process calls itself highly variable, so skipping is legitimate --
    but it has to leave a trace."""
    with pytest.raises(ValueError, match="requires a reason"):
        project.mark_step("request_source_erd", "skipped")

    project.mark_step("request_source_erd", "skipped", reason="Source is a flat file export")
    assert project.step_state("request_source_erd").reason


def test_skipped_counts_as_resolved(project):
    project.mark_step("request_source_erd", "skipped", reason="n/a")
    assert project.step_state("request_source_erd").is_resolved


def test_unknown_step_state_rejected(project):
    with pytest.raises(ValueError, match="Unknown step state"):
        project.mark_step("assign_roles", "in_progress")


# -- gates -------------------------------------------------------------------

def test_gate_blocks_until_prerequisites_are_resolved(project):
    blocking = project.blocking_for("gate_scope")
    assert blocking, "the first gate should start blocked"

    with pytest.raises(ValueError, match="outstanding prerequisite"):
        project.attest_gate("gate_scope", attested_by="Stakeholder")


def test_gate_passes_once_prerequisites_are_resolved(project):
    gate = next(g for g in load_process().gates if g.id == "gate_scope")
    for step_id in gate.requires:
        project.mark_step(step_id, "done")

    assert project.blocking_for("gate_scope") == []
    entry = project.attest_gate("gate_scope", attested_by="Alex Stakeholder")
    assert entry.passed
    assert entry.attested_by == "Alex Stakeholder"
    assert entry.attested_at


def test_attestation_must_name_someone(project):
    gate = next(g for g in load_process().gates if g.id == "gate_scope")
    for step_id in gate.requires:
        project.mark_step(step_id, "done")
    with pytest.raises(ValueError, match="name who signed off"):
        project.attest_gate("gate_scope", attested_by="   ")


def test_a_skipped_prerequisite_still_unblocks_the_gate(project):
    """Skipping is a recorded decision, not an omission."""
    gate = next(g for g in load_process().gates if g.id == "gate_scope")
    for step_id in gate.requires:
        project.mark_step(step_id, "skipped", reason="carried over from a prior project")
    assert project.blocking_for("gate_scope") == []


# -- size tailoring ----------------------------------------------------------

def test_small_projects_drop_the_conditional_integration_steps(tmp_path):
    small = start_project(tmp_path / "s", size="small")
    medium = start_project(tmp_path / "m", size="medium")
    assert small.overall_completion()["total"] < medium.overall_completion()["total"]


def test_next_step_walks_the_process_in_order(project):
    process = load_process()
    assert project.next_step().id == process.steps[0].id

    project.mark_step(process.steps[0].id, "done")
    assert project.next_step().id == process.steps[1].id


def test_next_step_is_none_when_everything_is_resolved(project):
    for step in load_process().steps:
        project.mark_step(step.id, "done")
    assert project.next_step() is None


def test_unknown_size_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unknown project size"):
        start_project(tmp_path, size="enormous")


def test_from_dict_ignores_unknown_keys(tmp_path, project):
    """Forward compatibility: a newer file must not crash an older build."""
    data = project.to_dict()
    data["some_future_field"] = True
    restored = ProjectState.from_dict(data)
    assert restored.name == project.name
