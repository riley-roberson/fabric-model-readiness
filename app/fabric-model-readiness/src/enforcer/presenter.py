"""Interactive terminal UI for presenting the change plan and collecting user decisions."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from shared.model import ChangeDecision, ChangePlan, ChangeProposal, Disposition, Severity

console = Console()

SEVERITY_COLORS = {
    Severity.CRITICAL: "red bold",
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "dim",
    Severity.INFO: "dim",
}


def present_plan(plan: ChangePlan) -> list[ChangeDecision]:
    """Display the full change plan and collect Accept/Reject/Defer/Edit for each item."""
    console.print()
    console.rule(f"PROPOSED CHANGES -- {plan.model_name} (Score: {plan.pre_score}/100)")
    console.print()

    if not plan.proposals:
        console.print("[green]No changes to propose.[/green]")
        return []

    decisions: list[ChangeDecision] = []
    current_severity: Severity | None = None

    for i, proposal in enumerate(plan.proposals, 1):
        # Print severity header when it changes
        if proposal.severity != current_severity:
            current_severity = proposal.severity
            color = SEVERITY_COLORS.get(current_severity, "")
            count = sum(1 for p in plan.proposals if p.severity == current_severity)
            console.print(f"\n[{color}]--- {current_severity.value.upper()} ({count} items) ---[/{color}]\n")

        decision = _present_single_proposal(i, proposal)
        decisions.append(decision)

    return decisions


def _present_single_proposal(index: int, proposal: ChangeProposal) -> ChangeDecision:
    """Present one proposal and get user decision."""
    color = SEVERITY_COLORS.get(proposal.severity, "")

    content = f"[{color}][{index}] {proposal.title}[/{color}]\n"
    content += f"    WHY: {proposal.why}\n"
    content += f"    CHANGE: {proposal.change_description}\n"

    if proposal.proposed_value:
        value_str = str(proposal.proposed_value)
        if len(value_str) > 100:
            value_str = value_str[:100] + "..."
        content += f'    PROPOSED VALUE: "{value_str}"\n'

    if proposal.impact:
        content += f"    [yellow]IMPACT: {proposal.impact}[/yellow]\n"

    console.print(Panel(content, expand=False))

    choice = Prompt.ask(
        "    Decision",
        choices=["a", "r", "d", "e"],
        default="a",
    )

    match choice:
        case "a":
            return ChangeDecision(finding_id=proposal.finding_id, disposition=Disposition.ACCEPTED)
        case "r":
            reason = Prompt.ask("    Reason for rejection", default="")
            return ChangeDecision(
                finding_id=proposal.finding_id,
                disposition=Disposition.REJECTED,
                reason=reason or None,
            )
        case "d":
            reason = Prompt.ask("    Reason for deferral", default="")
            return ChangeDecision(
                finding_id=proposal.finding_id,
                disposition=Disposition.DEFERRED,
                reason=reason or None,
            )
        case "e":
            edited = Prompt.ask("    Enter your edited value")
            return ChangeDecision(
                finding_id=proposal.finding_id,
                disposition=Disposition.ACCEPTED,
                edited_value=edited,
            )
        case _:
            return ChangeDecision(finding_id=proposal.finding_id, disposition=Disposition.DEFERRED)


def print_apply_summary(accepted: int, rejected: int, deferred: int) -> None:
    """Print a summary after all decisions are collected."""
    console.print()
    console.rule("Decision Summary")
    console.print(f"  Accepted: [green]{accepted}[/green]")
    console.print(f"  Rejected: [red]{rejected}[/red]")
    console.print(f"  Deferred: [yellow]{deferred}[/yellow]")
    console.print()
