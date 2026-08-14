"""Project state: where a project is in the process, and what it has done.

Persisted to `sidekick.json` at the **project root**, not inside the
.SemanticModel folder. The process starts months before a semantic model exists
-- bronze, silver, and gold are warehouse work -- so binding project state to
the model folder would leave the first five stages nowhere to live. Keeping it
at the root also means the file travels with the project and can be committed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sidekick.process import Process, load_process

STATE_FILENAME = "sidekick.json"
STATE_VERSION = 1

SIZES = {"small", "medium", "large"}
STEP_STATES = {"pending", "done", "skipped"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class StepState:
    state: str = "pending"
    note: str = ""
    reason: str = ""        # required when skipped
    updated_at: str = ""

    @property
    def is_resolved(self) -> bool:
        """Done or deliberately skipped -- either way, not outstanding."""
        return self.state in {"done", "skipped"}


@dataclass
class GateState:
    passed: bool = False
    attested_by: str = ""
    attested_at: str = ""
    note: str = ""


@dataclass
class ProjectState:
    version: int = STATE_VERSION
    name: str = ""
    root_path: str = ""
    model_path: str = ""
    size: str = "medium"
    current_stage: str = ""
    business_event: str = ""
    story_type: str = ""
    roles: dict[str, str] = field(default_factory=dict)
    steps: dict[str, StepState] = field(default_factory=dict)
    gates: dict[str, GateState] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    # -- step transitions ---------------------------------------------------

    def step_state(self, step_id: str) -> StepState:
        return self.steps.setdefault(step_id, StepState())

    def mark_step(self, step_id: str, state: str, *, note: str = "", reason: str = "") -> StepState:
        if state not in STEP_STATES:
            raise ValueError(f"Unknown step state '{state}'. Expected one of {sorted(STEP_STATES)}.")
        if state == "skipped" and not reason.strip():
            # The process document opens by calling itself "highly variable", so
            # skipping is legitimate -- but it has to leave a trace.
            raise ValueError("Skipping a step requires a reason.")

        entry = self.step_state(step_id)
        entry.state = state
        entry.note = note
        entry.reason = reason if state == "skipped" else ""
        entry.updated_at = _now()
        self.updated_at = entry.updated_at
        return entry

    # -- gates --------------------------------------------------------------

    def gate_state(self, gate_id: str) -> GateState:
        return self.gates.setdefault(gate_id, GateState())

    def blocking_for(self, gate_id: str, process: Process | None = None) -> list[str]:
        """Prerequisite steps that are still outstanding."""
        process = process or load_process()
        gate = next((g for g in process.gates if g.id == gate_id), None)
        if gate is None:
            raise KeyError(f"No such gate: {gate_id}")
        return [
            step_id for step_id in gate.requires
            if not self.step_state(step_id).is_resolved
        ]

    def attest_gate(
        self, gate_id: str, *, attested_by: str, note: str = "", process: Process | None = None
    ) -> GateState:
        """Record stakeholder sign-off. Refuses while prerequisites are open.

        Steps bend; gates do not. This is the one place the tool says no.
        """
        if not attested_by.strip():
            raise ValueError("A gate attestation must name who signed off.")

        blocking = self.blocking_for(gate_id, process)
        if blocking:
            raise ValueError(
                f"{gate_id} still has {len(blocking)} outstanding prerequisite(s): "
                + ", ".join(blocking)
            )

        entry = self.gate_state(gate_id)
        entry.passed = True
        entry.attested_by = attested_by.strip()
        entry.attested_at = _now()
        entry.note = note
        self.updated_at = entry.attested_at
        return entry

    # -- progress -----------------------------------------------------------

    def stage_completion(self, stage_id: str, process: Process | None = None) -> dict:
        process = process or load_process()
        steps = [s for s in process.steps_for(stage_id) if self._applies(s)]
        resolved = sum(1 for s in steps if self.step_state(s.id).is_resolved)
        return {
            "stage": stage_id,
            "total": len(steps),
            "resolved": resolved,
            "percent": round(100 * resolved / len(steps)) if steps else 100,
        }

    def overall_completion(self, process: Process | None = None) -> dict:
        process = process or load_process()
        steps = [s for s in process.steps if self._applies(s)]
        resolved = sum(1 for s in steps if self.step_state(s.id).is_resolved)
        return {
            "total": len(steps),
            "resolved": resolved,
            "percent": round(100 * resolved / len(steps)) if steps else 100,
        }

    def next_step(self, process: Process | None = None):
        """The first unresolved applicable step, in process order."""
        process = process or load_process()
        for step in process.steps:
            if self._applies(step) and not self.step_state(step.id).is_resolved:
                return step
        return None

    def _applies(self, step) -> bool:
        """Small projects skip integration work the doc marks as conditional."""
        condition = step.optional_when
        if not condition:
            return True
        if condition == "size == small":
            return self.size != "small"
        return True

    # -- persistence --------------------------------------------------------

    def to_dict(self) -> dict:
        data = asdict(self)
        data["steps"] = {k: asdict(v) if not isinstance(v, dict) else v for k, v in self.steps.items()}
        data["gates"] = {k: asdict(v) if not isinstance(v, dict) else v for k, v in self.gates.items()}
        return data

    @classmethod
    def from_dict(cls, data: dict) -> ProjectState:
        steps = {k: StepState(**v) for k, v in (data.get("steps") or {}).items()}
        gates = {k: GateState(**v) for k, v in (data.get("gates") or {}).items()}
        known = {f for f in cls.__dataclass_fields__}
        payload = {k: v for k, v in data.items() if k in known}
        payload["steps"] = steps
        payload["gates"] = gates
        return cls(**payload)


def state_path(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / STATE_FILENAME


def load_state(project_root: str | Path) -> ProjectState | None:
    path = state_path(project_root)
    if not path.is_file():
        return None
    try:
        return ProjectState.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError(f"{path} is not readable Sidekick state: {exc}") from exc


def save_state(state: ProjectState) -> Path:
    """Write atomically -- a half-written state file would lose the project."""
    path = state_path(state.root_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    temp.replace(path)
    return path


def start_project(
    project_root: str | Path,
    *,
    name: str = "",
    size: str = "medium",
    model_path: str = "",
) -> ProjectState:
    if size not in SIZES:
        raise ValueError(f"Unknown project size '{size}'. Expected one of {sorted(SIZES)}.")

    root = Path(project_root).resolve()
    process = load_process()
    state = ProjectState(
        name=name or root.name,
        root_path=str(root),
        model_path=model_path,
        size=size,
        current_stage=process.stages[0].id,
    )
    save_state(state)
    return state
