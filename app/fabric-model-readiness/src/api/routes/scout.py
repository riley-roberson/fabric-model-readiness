"""Scout API route: POST /api/scan with SSE progress streaming."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from scout import parser, report
from scout.report import sanitize_model_name
from scout.rules import filter_by_profile, run_all_checks
from scout.scorer import compute_summary, rating
from shared.model import Profile, ScanReport

router = APIRouter(prefix="/api", tags=["scout"])


class ScanRequest(BaseModel):
    path: str
    profile: str = "both"


class ScanResponse(BaseModel):
    scan_id: str
    model_path: str
    format: str
    profile: str
    score: float
    rating: str
    summary: dict
    findings: list[dict]


@router.post("/scan")
async def scan(request: ScanRequest) -> ScanResponse:
    """Run a full Scout scan on a PBIP folder or PBIX file."""
    # Validate profile
    try:
        active_profile = Profile(request.profile.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile '{request.profile}'. Must be ai, org, or both.",
        )

    model_path = Path(request.path)

    # Parse
    try:
        model = parser.parse(model_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse model: {e}")

    # Run checks and filter by profile
    findings = run_all_checks(model)
    findings = filter_by_profile(findings, active_profile)

    # Compute total checks per category
    total_checks: dict[str, int] = {}
    for f in findings:
        cat = f.category.value
        total_checks[cat] = total_checks.get(cat, 0) + 1
    for cat in total_checks:
        total_checks[cat] = max(total_checks[cat], int(total_checks[cat] / 0.6))

    summary = compute_summary(findings, total_checks)

    # Build and save report
    scan_report = ScanReport(
        model_path=str(model_path),
        format=model.format,
        profile=active_profile,
        summary=summary,
        findings=findings,
    )
    report.save_report(scan_report)

    return ScanResponse(
        scan_id=scan_report.scan_id,
        model_path=str(model_path),
        format=model.format.value,
        profile=active_profile.value,
        score=summary.score,
        rating=rating(summary.score),
        summary=summary.model_dump(),
        findings=[f.model_dump() for f in findings],
    )


@router.post("/scan/stream")
async def scan_stream(request: ScanRequest) -> EventSourceResponse:
    """Run a Scout scan with SSE progress updates."""
    # Validate profile early so we fail before streaming starts.
    try:
        active_profile = Profile(request.profile.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile '{request.profile}'. Must be ai, org, or both.",
        )

    async def generate() -> AsyncGenerator[dict, None]:
        model_path = Path(request.path)

        yield {"event": "progress", "data": json.dumps({"step": "parsing", "percent": 10, "message": f"Parsing {model_path.name}..."})}
        await asyncio.sleep(0)

        try:
            model = parser.parse(model_path)
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": f"Failed to parse model: {e}"})}
            return

        try:
            yield {"event": "progress", "data": json.dumps({"step": "rules", "percent": 30, "message": f"Running checks on {len(model.tables)} tables..."})}
            await asyncio.sleep(0)

            findings = run_all_checks(model)
            findings = filter_by_profile(findings, active_profile)

            yield {"event": "progress", "data": json.dumps({"step": "scoring", "percent": 80, "message": f"Scoring {len(findings)} findings..."})}
            await asyncio.sleep(0)

            total_checks: dict[str, int] = {}
            for f in findings:
                cat = f.category.value
                total_checks[cat] = total_checks.get(cat, 0) + 1
            for cat in total_checks:
                total_checks[cat] = max(total_checks[cat], int(total_checks[cat] / 0.6))

            summary = compute_summary(findings, total_checks)

            scan_report = ScanReport(
                model_path=str(model_path),
                format=model.format,
                profile=active_profile,
                summary=summary,
                findings=findings,
            )
            report.save_report(scan_report)

            yield {"event": "progress", "data": json.dumps({"step": "done", "percent": 100, "message": "Scan complete."})}

            yield {
                "event": "result",
                "data": json.dumps({
                    "scan_id": scan_report.scan_id,
                    "model_path": str(model_path),
                    "model_name": sanitize_model_name(str(model_path)),
                    "format": model.format.value,
                    "profile": active_profile.value,
                    "score": summary.score,
                    "rating": rating(summary.score),
                    "summary": summary.model_dump(),
                    "findings": [f.model_dump() for f in findings],
                }),
            }
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": f"Analysis failed: {e}"})}

    return EventSourceResponse(generate())
