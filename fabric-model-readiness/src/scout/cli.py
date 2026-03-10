"""Scout CLI: `scout analyze <path>`"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from scout import parser, report
from scout.rules import run_all_checks
from scout.scorer import compute_summary, rating
from shared.model import ScanReport, Severity

app = typer.Typer(help="Scout Agent -- Read-only semantic model analyzer")
console = Console()


@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to a .SemanticModel PBIP folder or .pbix file"),
) -> None:
    """Analyze a semantic model for Prep for AI best practices."""
    model_path = Path(path)
    console.print(f"\nAnalyzing: [bold]{model_path}[/bold]\n")

    # Parse
    try:
        model = parser.parse(model_path)
    except (FileNotFoundError, NotImplementedError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    console.print(f"Format: {model.format.value}")
    console.print(f"Tables: {len(model.tables)}")
    console.print()

    # Run checks
    findings = run_all_checks(model)

    # Compute total checks per category (findings count as checks that failed)
    # For a proper denominator we count total objects checked per category.
    # Simplified: total checks = number of findings + estimated passing checks.
    # TODO: Rule modules should return (findings, total_checked) for accuracy.
    total_checks: dict[str, int] = {}
    for f in findings:
        cat = f.category.value
        total_checks[cat] = total_checks.get(cat, 0) + 1
    # Rough estimate: assume each finding represents ~60% failure rate
    for cat in total_checks:
        total_checks[cat] = max(total_checks[cat], int(total_checks[cat] / 0.6))

    summary = compute_summary(findings, total_checks)

    # Build report
    scan_report = ScanReport(
        model_path=str(model_path),
        format=model.format,
        summary=summary,
        findings=findings,
    )

    # Save
    report_path = report.save_report(scan_report)

    # Display
    _print_summary(summary)
    _print_findings(findings)
    console.print(f"\nReport saved: [dim]{report_path}[/dim]\n")


def _print_summary(summary):
    score_color = "green" if summary.score >= 75 else "yellow" if summary.score >= 50 else "red"
    console.print(f"Score: [{score_color}]{summary.score}/100[/{score_color}] -- {rating(summary.score)}")
    console.print(
        f"Critical: {summary.critical}  High: {summary.high}  "
        f"Medium: {summary.medium}  Low: {summary.low}  Info: {summary.info}"
    )


def _print_findings(findings):
    if not findings:
        console.print("\n[green]No findings. Model looks good.[/green]")
        return

    table = Table(title="\nFindings", show_lines=True)
    table.add_column("Severity", width=10)
    table.add_column("Category", width=22)
    table.add_column("Object", width=30)
    table.add_column("Message", width=60)

    severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3, Severity.INFO: 4}
    sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity, 5))

    severity_colors = {
        Severity.CRITICAL: "red bold",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "dim",
        Severity.INFO: "dim",
    }

    for f in sorted_findings:
        color = severity_colors.get(f.severity, "")
        table.add_row(
            f"[{color}]{f.severity.value}[/{color}]",
            f.category.value,
            f.object,
            f.message,
        )

    console.print(table)


if __name__ == "__main__":
    app()
