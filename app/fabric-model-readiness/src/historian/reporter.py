"""Summary reports: score trends, category breakdowns, narrative summaries."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from shared.llm import generate_narrative_summary
from shared.model import Disposition, ModelHistory

console = Console()


def print_history_report(history: ModelHistory) -> None:
    """Print a formatted history report to the terminal."""
    console.print(f"\n[bold]History: {history.model_name}[/bold]")
    console.print(f"Total sessions: {len(history.sessions)}\n")

    if not history.sessions:
        console.print("[dim]No sessions recorded yet.[/dim]")
        return

    # Score trend table
    score_table = Table(title="Score Trend")
    score_table.add_column("Date", width=20)
    score_table.add_column("Scan ID", width=12)
    score_table.add_column("Pre-Score", width=10)
    score_table.add_column("Accepted", width=10)
    score_table.add_column("Rejected", width=10)
    score_table.add_column("Deferred", width=10)

    for session in history.sessions:
        accepted = sum(1 for c in session.changes if c.action == Disposition.ACCEPTED)
        rejected = sum(1 for c in session.changes if c.action == Disposition.REJECTED)
        deferred = sum(1 for c in session.changes if c.action == Disposition.DEFERRED)

        score_table.add_row(
            str(session.timestamp)[:19],
            session.scan_id[:12],
            str(session.pre_score),
            str(accepted),
            str(rejected),
            str(deferred),
        )

    console.print(score_table)


def generate_report_narrative(history: ModelHistory) -> str:
    """Use the LLM to generate an executive-friendly summary of scan history."""
    history_data = json.dumps(history.model_dump(mode="json"), indent=2, default=str)
    return generate_narrative_summary(history_data)
