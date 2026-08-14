"""Enforcer API routes.

POST /api/apply          -- record decisions and write the accepted ones
POST /api/apply/preview  -- show what would be written, touching nothing
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from enforcer import executor
from enforcer.planner import build_change_plan
from historian.logger import record_session
from scout import parser
from scout.report import load_latest_report
from scout.rules import run_all_checks
from scout.scorer import compute_summary
from shared.model import ChangeDecision, ChangeRecord, Disposition

router = APIRouter(prefix="/api", tags=["enforcer"])


class DecisionInput(BaseModel):
    finding_id: str
    action: str  # "accepted", "rejected", "deferred"
    reason: str | None = None
    edited_value: str | None = None


class ApplyRequest(BaseModel):
    scan_id: str
    model_name: str
    decisions: list[DecisionInput]


class ApplyResponse(BaseModel):
    applied: int
    deferred: int
    rejected: int
    new_score: float | None
    history_path: str
    # Populated when changes were actually written to the model.
    unsupported: list[dict] = []
    failed: list[dict] = []
    backup_path: str | None = None
    rolled_back: bool = False
    error: str | None = None


class PreviewRequest(BaseModel):
    scan_id: str
    model_name: str
    finding_ids: list[str]
    values: dict[str, str] = {}


class PreviewResponse(BaseModel):
    changes: list[dict]
    unsupported: list[dict]


@router.post("/apply")
async def apply_decisions(request: ApplyRequest) -> ApplyResponse:
    """Record all decisions via Historian. Changes are applied via Claude Code + MCP."""
    # Load the scan report
    report = load_latest_report(request.model_name)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No scan found for model: {request.model_name}")

    if report.scan_id != request.scan_id:
        raise HTTPException(status_code=409, detail="Scan ID mismatch. Run a new scan first.")

    plan = build_change_plan(report)

    # Build decision map
    decision_map: dict[str, DecisionInput] = {d.finding_id: d for d in request.decisions}

    # Convert to ChangeDecision + ChangeRecord lists
    change_decisions: list[ChangeDecision] = []
    change_records: list[ChangeRecord] = []

    accepted_count = 0
    deferred_count = 0
    rejected_count = 0

    for proposal in plan.proposals:
        decision_input = decision_map.get(proposal.finding_id)
        if decision_input is None:
            continue

        disposition = Disposition(decision_input.action)

        change_decisions.append(ChangeDecision(
            finding_id=proposal.finding_id,
            disposition=disposition,
            reason=decision_input.reason,
            edited_value=decision_input.edited_value,
        ))

        change_records.append(ChangeRecord(
            finding_id=proposal.finding_id,
            category=proposal.category,
            object=proposal.object,
            action=disposition,
            description=proposal.change_description,
            before=None,
            after=proposal.proposed_value if disposition == Disposition.ACCEPTED else None,
            reason=decision_input.reason,
        ))

        match disposition:
            case Disposition.ACCEPTED:
                accepted_count += 1
            case Disposition.DEFERRED:
                deferred_count += 1
            case Disposition.REJECTED:
                rejected_count += 1

    plan.decisions = change_decisions

    # Write the accepted changes to the model. Everything above this point only
    # recorded intent; this is the step that touches the user's files.
    accepted_ids = {
        d.finding_id for d in change_decisions if d.disposition == Disposition.ACCEPTED
    }
    accepted_findings = [f for f in report.findings if f.id in accepted_ids]

    execution = None
    if accepted_findings:
        values = {
            d.finding_id: d.edited_value
            for d in change_decisions
            if d.edited_value is not None
        }
        try:
            execution = executor.apply(report.model_path, accepted_findings, values)
        except Exception as exc:  # noqa: BLE001 -- surfaced to the caller verbatim
            raise HTTPException(status_code=500, detail=f"Apply failed: {exc}") from exc

        # Record what actually happened, not what was requested.
        applied_ids = {
            r.finding_id for r in execution.results if r.status == "applied"
        }
        for record in change_records:
            if record.action != Disposition.ACCEPTED:
                continue
            operation = next(
                (o for o in execution.operations if o.finding_id == record.finding_id), None
            )
            if operation is not None:
                record.before = operation.before
                record.after = operation.value if record.finding_id in applied_ids else None

    # Record session via Historian
    history_path = record_session(plan, change_records)

    if execution is None:
        return ApplyResponse(
            applied=0,
            deferred=deferred_count,
            rejected=rejected_count,
            new_score=None,
            history_path=str(history_path),
        )

    # Re-scan so the post-change score is measured rather than projected.
    new_score = None
    if execution.applied and not execution.rolled_back:
        try:
            rescanned = parser.parse(Path(report.model_path))
            findings = run_all_checks(rescanned)
            new_score = compute_summary(findings, len(findings)).score
        except Exception:
            new_score = None  # a failed re-scan must not fail the apply

    return ApplyResponse(
        applied=execution.applied,
        deferred=deferred_count,
        rejected=rejected_count,
        new_score=new_score,
        history_path=str(history_path),
        unsupported=[
            {"finding_id": u.finding_id, "check": u.check, "object": u.object, "reason": u.reason}
            for u in execution.unsupported
        ],
        failed=[
            {"finding_id": r.finding_id, "object": r.operation.target, "detail": r.detail}
            for r in execution.results if r.status != "applied"
        ],
        backup_path=execution.backup_path,
        rolled_back=execution.rolled_back,
        error=execution.error,
    )


@router.post("/apply/preview")
async def preview_changes(request: PreviewRequest) -> PreviewResponse:
    """Show exactly what would be written, without writing anything."""
    report = load_latest_report(request.model_name)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No scan found for model: {request.model_name}")
    if report.scan_id != request.scan_id:
        raise HTTPException(status_code=409, detail="Scan ID mismatch. Run a new scan first.")

    wanted = set(request.finding_ids)
    findings = [f for f in report.findings if f.id in wanted]

    try:
        result = executor.preview(report.model_path, findings, dict(request.values))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Preview failed: {exc}") from exc

    return PreviewResponse(
        changes=[
            {
                "finding_id": op.finding_id,
                "check": op.check,
                "object": op.target,
                "property": op.prop,
                "before": op.before,
                "after": op.value,
            }
            for op in result.operations
        ],
        unsupported=[
            {"finding_id": u.finding_id, "check": u.check, "object": u.object, "reason": u.reason}
            for u in result.unsupported
        ],
    )
