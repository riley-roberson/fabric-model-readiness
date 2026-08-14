"""The Semantic Model Development Process, as data.

process.json is the single encoding of the org's development process. It is kept
as data rather than code so the document owner can amend it without touching
Python, and it carries a doc_revision stamp so drift from the source .docx is
visible rather than silent.

Steps are tagged with a `source`:

  doc       -- taken verbatim from the process document
  proposed  -- not in the document. Currently only the AI Readiness stage, which
               exists because the process has no Prep for AI step and the 20
               Data Agent checks would otherwise have nowhere to attach. It is
               flagged so the tool is never mistaken for org process that the
               document owner has actually ratified.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

PROCESS_FILE = Path(__file__).with_name("process.json")

# How a step proves itself done.
EVIDENCE_KINDS = {"manual", "artifact", "lint", "naming", "derived", "external"}


@dataclass(frozen=True)
class Step:
    id: str
    stage_id: str
    index: int              # 1-based position across the whole process
    text: str
    source: str
    evidence: str
    detail: str = ""
    checks: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    layer: str = ""
    derived: str = ""
    optional_when: str = ""

    @property
    def is_proposed(self) -> bool:
        return self.source != "doc"

    @property
    def auto_verifiable(self) -> bool:
        """Evidence the tool can establish without asking the user."""
        return self.evidence in {"lint", "naming", "derived", "artifact"}


@dataclass(frozen=True)
class Gate:
    id: str
    stage_id: str
    text: str
    source: str
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Stage:
    id: str
    phase: str
    title: str
    steps: tuple[Step, ...]
    gate: Gate | None = None
    proposed: bool = False
    proposal_note: str = ""
    # Advice that belongs at this stage even though it is enforced at a later
    # one. Descriptions are the motivating case: checking them here would bury
    # everything else, but writing them here costs a fraction of retrofitting.
    heads_up: str = ""


@dataclass(frozen=True)
class Process:
    source_document: str
    doc_revision: str
    stages: tuple[Stage, ...]
    steps: tuple[Step, ...] = field(default=())

    @property
    def gates(self) -> tuple[Gate, ...]:
        return tuple(s.gate for s in self.stages if s.gate is not None)

    @property
    def doc_steps(self) -> tuple[Step, ...]:
        return tuple(s for s in self.steps if s.source == "doc")

    @property
    def doc_item_count(self) -> int:
        """Steps plus gates that came from the document.

        This is the number that must match the source .docx, and the drift
        test asserts it.
        """
        return len(self.doc_steps) + sum(1 for g in self.gates if g.source == "doc")

    def stage(self, stage_id: str) -> Stage:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(f"No such stage: {stage_id}")

    def step(self, step_id: str) -> Step:
        for step in self.steps:
            if step.id == step_id:
                return step
        raise KeyError(f"No such step: {step_id}")

    def steps_for(self, stage_id: str) -> tuple[Step, ...]:
        return self.stage(stage_id).steps

    def stage_index(self, stage_id: str) -> int:
        """1-based, for 'Stage 4 of 11'."""
        for i, stage in enumerate(self.stages, start=1):
            if stage.id == stage_id:
                return i
        raise KeyError(f"No such stage: {stage_id}")

    def stages_up_to(self, stage_id: str) -> tuple[Stage, ...]:
        """Every stage from the beginning through the given one."""
        cutoff = self.stage_index(stage_id)
        return self.stages[:cutoff]


@lru_cache(maxsize=1)
def load_process() -> Process:
    raw = json.loads(PROCESS_FILE.read_text(encoding="utf-8"))

    stages: list[Stage] = []
    all_steps: list[Step] = []
    counter = 0

    for raw_stage in raw["stages"]:
        stage_id = raw_stage["id"]
        steps: list[Step] = []

        for raw_step in raw_stage["steps"]:
            evidence = raw_step["evidence"]
            if evidence not in EVIDENCE_KINDS:
                raise ValueError(
                    f"Step {raw_step['id']} declares unknown evidence '{evidence}'. "
                    f"Expected one of: {', '.join(sorted(EVIDENCE_KINDS))}"
                )

            counter += 1
            step = Step(
                id=raw_step["id"],
                stage_id=stage_id,
                index=counter,
                text=raw_step["text"],
                source=raw_step.get("source", "doc"),
                evidence=evidence,
                detail=raw_step.get("detail", ""),
                checks=tuple(raw_step.get("checks", ())),
                artifacts=tuple(raw_step.get("artifacts", ())),
                layer=raw_step.get("layer", ""),
                derived=raw_step.get("derived", ""),
                optional_when=raw_step.get("optional_when", ""),
            )
            steps.append(step)
            all_steps.append(step)

        raw_gate = raw_stage.get("gate")
        gate = None
        if raw_gate:
            gate = Gate(
                id=raw_gate["id"],
                stage_id=stage_id,
                text=raw_gate["text"],
                source=raw_gate.get("source", "doc"),
                requires=tuple(raw_gate.get("requires", ())),
            )

        stages.append(Stage(
            id=stage_id,
            phase=raw_stage["phase"],
            title=raw_stage["title"],
            steps=tuple(steps),
            gate=gate,
            proposed=bool(raw_stage.get("proposed", False)),
            proposal_note=raw_stage.get("proposal_note", ""),
            heads_up=raw_stage.get("heads_up", ""),
        ))

    return Process(
        source_document=raw["source_document"],
        doc_revision=raw["doc_revision"],
        stages=tuple(stages),
        steps=tuple(all_steps),
    )
