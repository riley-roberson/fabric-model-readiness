"""Historian CLI: `historian log`, `historian log --model <name>`"""

from __future__ import annotations

import typer
from rich.console import Console

from historian.logger import list_models, load_history
from historian.reporter import generate_report_narrative, print_history_report
from historian.resurface import get_deferred_items

app = typer.Typer(help="Historian Agent -- Change history tracker")
console = Console()


@app.command()
def log(
    model: str = typer.Option("", help="Model name to show history for. Lists all models if omitted."),
    narrative: bool = typer.Option(False, "--narrative", "-n", help="Generate an LLM narrative summary."),
) -> None:
    """View change history for a model."""
    if not model:
        models = list_models()
        if not models:
            console.print("[dim]No history recorded yet. Run a scan and review cycle first.[/dim]")
            raise typer.Exit()
        console.print("\n[bold]Models with history:[/bold]")
        for m in models:
            console.print(f"  - {m}")
        console.print(f"\nUse [bold]historian log --model <name>[/bold] to view details.\n")
        raise typer.Exit()

    history = load_history(model)
    if not history:
        console.print(f"[red]No history found for model '{model}'.[/red]")
        raise typer.Exit(code=1)

    print_history_report(history)

    # Show deferred items
    deferred = get_deferred_items(history)
    if deferred:
        console.print(f"\n[yellow]Deferred items ({len(deferred)}):[/yellow]")
        for item in deferred:
            reason = item.get("reason", "no reason given")
            console.print(f"  - {item['object']} ({item['category']}): {reason}")

    # Optional narrative
    if narrative:
        console.print("\n[bold]Generating narrative summary...[/bold]")
        summary = generate_report_narrative(history)
        console.print(f"\n{summary}\n")


if __name__ == "__main__":
    app()
