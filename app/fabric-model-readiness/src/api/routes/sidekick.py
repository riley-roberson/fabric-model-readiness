"""Sidekick API: the guided walkthrough of a semantic model project.

GET  /api/sidekick/process          the encoded process, for rendering the spine
POST /api/sidekick/project          start or load a project
GET  /api/sidekick/project          current state, progress, and next step
POST /api/sidekick/step             mark a step done or skipped
POST /api/sidekick/gate             record a stakeholder attestation
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scout import parser
from scout.rules import run_all_checks
from sidekick.process import load_process
from sidekick.stages import filter_by_stage, stage_progress
from sidekick.state import load_state, save_state, start_project

router = APIRouter(prefix="/api/sidekick", tags=["sidekick"])


class StartProjectRequest(BaseModel):
    root_path: str
    name: str = ""
    size: str = "medium"
    model_path: str = ""


class StepRequest(BaseModel):
    root_path: str
    step_id: str
    state: str          # done | skipped | pending
    note: str = ""
    reason: str = ""


class GateRequest(BaseModel):
    root_path: str
    gate_id: str
    attested_by: str
    note: str = ""


class StageRequest(BaseModel):
    root_path: str
    stage_id: str


def _require_state(root_path: str):
    try:
        state = load_state(root_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No Sidekick project at {root_path}. Start one first.",
        )
    return state


def _serialize_process() -> dict:
    process = load_process()
    return {
        "source_document": process.source_document,
        "doc_revision": process.doc_revision,
        "total_steps": len(process.steps),
        "stages": [
            {
                "id": stage.id,
                "phase": stage.phase,
                "title": stage.title,
                "proposed": stage.proposed,
                "proposal_note": stage.proposal_note,
                "steps": [
                    {
                        "id": step.id,
                        "index": step.index,
                        "text": step.text,
                        "detail": step.detail,
                        "evidence": step.evidence,
                        "checks": list(step.checks),
                        "artifacts": list(step.artifacts),
                        "layer": step.layer,
                        "optional_when": step.optional_when,
                        "proposed": step.is_proposed,
                        "auto_verifiable": step.auto_verifiable,
                    }
                    for step in stage.steps
                ],
                "gate": None if stage.gate is None else {
                    "id": stage.gate.id,
                    "text": stage.gate.text,
                    "requires": list(stage.gate.requires),
                },
            }
            for stage in process.stages
        ],
    }


def _serialize_state(state) -> dict:
    process = load_process()
    next_step = state.next_step(process)

    gates = {}
    for gate in process.gates:
        entry = state.gate_state(gate.id)
        gates[gate.id] = {
            "passed": entry.passed,
            "attested_by": entry.attested_by,
            "attested_at": entry.attested_at,
            "note": entry.note,
            "blocking": state.blocking_for(gate.id, process),
        }

    return {
        "name": state.name,
        "root_path": state.root_path,
        "model_path": state.model_path,
        "size": state.size,
        "current_stage": state.current_stage,
        "current_stage_index": process.stage_index(state.current_stage),
        "stage_count": len(process.stages),
        "steps": {
            step_id: {
                "state": entry.state,
                "note": entry.note,
                "reason": entry.reason,
                "updated_at": entry.updated_at,
            }
            for step_id, entry in state.steps.items()
        },
        "gates": gates,
        "completion": state.overall_completion(process),
        "stage_completion": state.stage_completion(state.current_stage, process),
        "next_step": None if next_step is None else {
            "id": next_step.id,
            "index": next_step.index,
            "text": next_step.text,
            "stage_id": next_step.stage_id,
        },
    }


@router.get("/process")
async def get_process() -> dict:
    return _serialize_process()


@router.post("/project")
async def create_project(request: StartProjectRequest) -> dict:
    root = Path(request.root_path)
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {root}")

    existing = load_state(root)
    if existing is not None:
        return {"created": False, "state": _serialize_state(existing)}

    try:
        state = start_project(
            root, name=request.name, size=request.size, model_path=request.model_path
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"created": True, "state": _serialize_state(state)}


@router.get("/project")
async def get_project(root_path: str) -> dict:
    return _serialize_state(_require_state(root_path))


@router.post("/step")
async def update_step(request: StepRequest) -> dict:
    state = _require_state(request.root_path)
    try:
        load_process().step(request.step_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        state.mark_step(request.step_id, request.state, note=request.note, reason=request.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    save_state(state)
    return _serialize_state(state)


@router.post("/gate")
async def attest_gate(request: GateRequest) -> dict:
    """Record stakeholder sign-off.

    Refuses while prerequisites are open. Steps bend; gates do not.
    """
    state = _require_state(request.root_path)
    try:
        state.attest_gate(request.gate_id, attested_by=request.attested_by, note=request.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    save_state(state)
    return _serialize_state(state)


@router.post("/stage")
async def set_stage(request: StageRequest) -> dict:
    state = _require_state(request.root_path)
    try:
        load_process().stage(request.stage_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    state.current_stage = request.stage_id
    save_state(state)
    return _serialize_state(state)


@router.get("/findings")
async def stage_findings(root_path: str) -> dict:
    """Findings that matter *now*, plus how many were held back.

    Reporting all 64 checks against a half-built model is the behaviour this
    endpoint exists to replace.
    """
    state = _require_state(root_path)
    if not state.model_path:
        return {
            "stage": state.current_stage,
            "findings": [],
            "progress": stage_progress([], state.current_stage),
            "message": "No semantic model linked to this project yet.",
        }

    try:
        model = parser.parse(Path(state.model_path))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not parse the model: {exc}") from exc

    all_findings = run_all_checks(model)
    scoped = filter_by_stage(all_findings, state.current_stage)

    return {
        "stage": state.current_stage,
        "progress": stage_progress(all_findings, state.current_stage),
        "findings": [
            {
                "id": f.id,
                "check": f.check,
                "category": f.category.value,
                "severity": f.severity.value,
                "object": f.object,
                "message": f.message,
                "recommendation": f.recommendation,
                "auto_fixable": f.auto_fixable,
            }
            for f in scoped
        ],
    }
