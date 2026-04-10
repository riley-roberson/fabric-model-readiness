"""Enforcer API route: POST /api/apply to accept/reject/defer findings and record decisions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from enforcer.planner import build_change_plan
from historian.logger import record_session
from scout.report import load_latest_report
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

    # Record session via Historian
    history_path = record_session(plan, change_records)

    return ApplyResponse(
        applied=accepted_count,
        deferred=deferred_count,
        rejected=rejected_count,
        new_score=None,  # Would require a re-scan
        history_path=str(history_path),
    )
