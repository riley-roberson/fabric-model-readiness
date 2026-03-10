"""Enforcer CLI: `enforcer review`"""

from __future__ import annotations

import typer
from rich.console import Console

from enforcer.planner import build_change_plan
from enforcer.presenter import present_plan, print_apply_summary
from historian.logger import record_session
from scout.report import load_latest_report
from shared.model import ChangeRecord, Disposition

app = typer.Typer(help="Enforcer Agent -- Review proposed changes and record decisions")
console = Console()


@app.command()
def review(
    model: str = typer.Option("", help="Model name to review. Uses latest scan if omitted."),
    scan_path: str = typer.Option("", help="Path to a specific scan JSON file."),
) -> None:
    """Review proposed changes from the latest scan and record decisions."""
    # Load scan report
    if scan_path:
        import json
        from pathlib import Path

        from shared.model import ScanReport

        data = json.loads(Path(scan_path).read_text(encoding="utf-8"))
        report = ScanReport(**data)
    else:
        report = load_latest_report(model)
        if not report:
            console.print("[red]No scan report found. Run 'scout analyze' first.[/red]")
            raise typer.Exit(code=1)

    # Build change plan
    console.print(f"\nBuilding change plan from scan [bold]{report.scan_id}[/bold]...")
    plan = build_change_plan(report)

    # Present to user and collect decisions
    decisions = present_plan(plan)

    if not decisions:
        raise typer.Exit()

    accepted = sum(1 for d in decisions if d.disposition == Disposition.ACCEPTED)
    rejected = sum(1 for d in decisions if d.disposition == Disposition.REJECTED)
    deferred = sum(1 for d in decisions if d.disposition == Disposition.DEFERRED)

    print_apply_summary(accepted, rejected, deferred)

    # Build change records from decisions
    proposal_map = {p.finding_id: p for p in plan.proposals}
    records: list[ChangeRecord] = []
    for decision in decisions:
        proposal = proposal_map.get(decision.finding_id)
        if not proposal:
            continue
        records.append(ChangeRecord(
            finding_id=decision.finding_id,
            category=proposal.category,
            object=proposal.object,
            action=decision.disposition,
            description=proposal.change_description,
            before=None,
            after=proposal.proposed_value if decision.disposition == Disposition.ACCEPTED else None,
            reason=decision.reason,
        ))

    # Record session for Historian
    plan.decisions = decisions
    record_session(plan, records)

    console.print("\n[green]Done.[/green] Decisions recorded for the Historian.")
    if accepted > 0:
        console.print(
            "To apply accepted changes to Power BI Desktop, run [bold]/enforcer[/bold] in Claude Code."
        )


if __name__ == "__main__":
    app()
