"""The encoded process must stay faithful to the source document."""

from __future__ import annotations

import pytest

from shared.config import CHECK_PROFILES
from sidekick.process import EVIDENCE_KINDS, load_process

# Counted from Semantic Model Development Process.docx: every bulleted action
# under a heading, including the four stakeholder acceptance items.
DOC_ITEM_COUNT = 59
DOC_GATE_COUNT = 4


@pytest.fixture(scope="module")
def process():
    return load_process()


def test_doc_item_count_matches_the_document(process):
    """The drift alarm.

    If someone edits the .docx and not process.json -- or the reverse -- this
    is what notices. A mismatch means the encoded process and the org's actual
    process have diverged.
    """
    assert process.doc_item_count == DOC_ITEM_COUNT, (
        f"Encoded {process.doc_item_count} document items, expected {DOC_ITEM_COUNT}. "
        f"Either {process.source_document} changed, or process.json drifted from it."
    )


def test_four_stakeholder_gates(process):
    assert len(process.gates) == DOC_GATE_COUNT
    assert all(g.source == "doc" for g in process.gates)


def test_step_ids_are_unique(process):
    ids = [s.id for s in process.steps]
    assert len(ids) == len(set(ids)), "duplicate step ids"


def test_step_indexes_are_contiguous(process):
    """Steps are numbered across the whole process for 'Step 23 of 59'."""
    assert [s.index for s in process.steps] == list(range(1, len(process.steps) + 1))


def test_evidence_kinds_are_known(process):
    for step in process.steps:
        assert step.evidence in EVIDENCE_KINDS


def test_lint_steps_reference_real_checks(process):
    """A step demanding a check that does not exist could never be satisfied."""
    unknown = {
        (step.id, check)
        for step in process.steps
        for check in step.checks
        if check not in CHECK_PROFILES
    }
    assert not unknown, f"steps reference unknown checks: {sorted(unknown)}"


def test_lint_steps_actually_declare_checks(process):
    for step in process.steps:
        if step.evidence == "lint":
            assert step.checks, f"{step.id} claims lint evidence but names no checks"


def test_gate_prerequisites_exist(process):
    """A gate can only require steps that are in the process."""
    step_ids = {s.id for s in process.steps}
    for gate in process.gates:
        missing = set(gate.requires) - step_ids
        assert not missing, f"{gate.id} requires unknown steps: {sorted(missing)}"


def test_gate_prerequisites_precede_their_gate(process):
    """Requiring a later step would make the gate unreachable."""
    for stage in process.stages:
        if stage.gate is None:
            continue
        cutoff = max(s.index for s in stage.steps)
        for required in stage.gate.requires:
            assert process.step(required).index <= cutoff, (
                f"{stage.gate.id} requires {required}, which comes after the gate"
            )


def test_proposed_steps_are_confined_to_the_proposed_stage(process):
    """Anything not in the document must be visibly flagged as such.

    The AI Readiness stage exists because the process document has no Prep for
    AI step. Until the document owner ratifies it, the tool must not present it
    as established org process.
    """
    proposed_stages = {s.id for s in process.stages if s.proposed}
    for step in process.steps:
        if step.is_proposed:
            assert step.stage_id in proposed_stages, (
                f"{step.id} is not from the document but sits in an unflagged stage"
            )

    for stage in process.stages:
        if stage.proposed:
            assert stage.proposal_note, f"{stage.id} is proposed but explains nothing"


def test_naming_steps_declare_a_layer(process):
    for step in process.steps:
        if step.evidence == "naming":
            assert step.layer, f"{step.id} claims naming evidence but names no layer"
