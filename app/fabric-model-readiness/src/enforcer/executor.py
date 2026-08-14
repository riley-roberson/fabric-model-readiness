"""Applies accepted findings to a semantic model on disk.

Order matters and is not negotiable:

    backup -> connect -> update (in memory) -> export -> re-parse -> verify

The re-parse is the point. The MCP reports success per Update call, but those
succeed against an in-memory model; the only evidence a change reached disk is
reading the folder back. If verification fails the backup is restored, so a run
either lands completely or not at all.

`dry_run=True` stops after building the operation list, which is what the
preview UI shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from enforcer.backup import Backup, create_backup, restore_backup
from enforcer.mcp_client import McpError, PowerBiMcpClient
from enforcer.operations import (
    ChangeOperation,
    UnsupportedChange,
    build_operations,
)
from scout import parser
from shared.model import Finding, SemanticModel

ProgressFn = Callable[[str], None]


@dataclass
class OperationResult:
    operation: ChangeOperation
    status: str          # applied | failed | unverified
    detail: str = ""

    @property
    def finding_id(self) -> str:
        return self.operation.finding_id


@dataclass
class ExecutionReport:
    model_path: str
    dry_run: bool
    operations: list[ChangeOperation] = field(default_factory=list)
    unsupported: list[UnsupportedChange] = field(default_factory=list)
    results: list[OperationResult] = field(default_factory=list)
    backup_path: str | None = None
    rolled_back: bool = False
    error: str | None = None

    @property
    def applied(self) -> int:
        return sum(1 for r in self.results if r.status == "applied")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status != "applied")

    def summary(self) -> str:
        if self.dry_run:
            return f"{len(self.operations)} change(s) ready, {len(self.unsupported)} unsupported"
        if self.rolled_back:
            return f"rolled back: {self.error}"
        return f"{self.applied} applied, {self.failed} failed, {len(self.unsupported)} unsupported"


def preview(model_path: str | Path, findings: list[Finding], values: dict[str, Any] | None = None) -> ExecutionReport:
    """Build the operation list without touching anything."""
    model = parser.parse(Path(model_path))
    operations, unsupported = build_operations(model, findings, values)
    return ExecutionReport(
        model_path=str(model_path),
        dry_run=True,
        operations=operations,
        unsupported=unsupported,
    )


def apply(
    model_path: str | Path,
    findings: list[Finding],
    values: dict[str, Any] | None = None,
    *,
    progress: ProgressFn | None = None,
    skip_backup: bool = False,
) -> ExecutionReport:
    """Apply accepted findings, verifying against disk and rolling back on failure."""
    say = progress or (lambda _msg: None)
    root = Path(model_path).resolve()

    model = parser.parse(root)
    operations, unsupported = build_operations(model, findings, values)

    report = ExecutionReport(
        model_path=str(root),
        dry_run=False,
        operations=operations,
        unsupported=unsupported,
    )

    if not operations:
        say("Nothing to apply.")
        return report

    backup: Backup | None = None
    if not skip_backup:
        say("Backing up the model...")
        backup = create_backup(root, tag="enforce")
        report.backup_path = str(backup.backup_path)

    try:
        with PowerBiMcpClient() as client:
            say("Connecting to the model folder...")
            connected = client.connect_folder(root)
            if not connected.success:
                raise McpError(f"Could not open the model: {connected.message}")

            _send_updates(client, operations, say)

            say("Writing changes to disk...")
            exported = client.export_to_folder(root)
            if not exported.success:
                raise McpError(f"Export failed: {exported.message}")

        say("Verifying against the model on disk...")
        report.results = _verify(root, operations)

        unverified = [r for r in report.results if r.status != "applied"]
        if unverified:
            raise McpError(
                f"{len(unverified)} change(s) did not survive the round-trip: "
                + ", ".join(r.operation.target for r in unverified[:5])
            )

    except Exception as exc:
        report.error = str(exc)
        if backup is not None:
            say("Rolling back...")
            restore_backup(backup)
            report.rolled_back = True
        return report

    say(report.summary())
    return report


def _send_updates(client: PowerBiMcpClient, operations: list[ChangeOperation], say: ProgressFn) -> None:
    """Batch by object kind; the MCP wraps each batch in its own transaction."""
    senders = {
        "table": client.update_tables,
        "column": client.update_columns,
        "measure": client.update_measures,
    }

    for kind, send in senders.items():
        batch = [op for op in operations if op.kind == kind]
        if not batch:
            continue
        say(f"Updating {len(batch)} {kind}(s)...")
        # One definition per property write: merging two writes to the same
        # object into one entry would silently drop one of them.
        result = send([op.to_definition() for op in batch])
        if not result.success:
            raise McpError(f"{kind} update failed: {result.message}")


def _verify(root: Path, operations: list[ChangeOperation]) -> list[OperationResult]:
    """Re-parse the folder and confirm each change is actually present."""
    fresh = parser.parse(root)
    tables = {t.name: t for t in fresh.tables}
    columns = {(t.name, c.name): c for t in fresh.tables for c in t.columns}
    measures = {(t.name, m.name): m for t in fresh.tables for m in t.measures}

    attr_for = {
        "description": "description",
        "isHidden": "is_hidden",
        "dataCategory": "data_category",
        "summarizeBy": "summarize_by",
        "sortByColumn": "sort_by_column",
        "displayFolder": "display_folder",
        "defaultLabel": "is_default_label",
        "dataType": "data_type",
    }

    results: list[OperationResult] = []
    for op in operations:
        obj = (
            tables.get(op.table) if op.kind == "table"
            else columns.get((op.table, op.name)) if op.kind == "column"
            else measures.get((op.table, op.name))
        )
        if obj is None:
            results.append(OperationResult(op, "failed", "Object not found after write"))
            continue

        attr = attr_for.get(op.prop)
        actual = getattr(obj, attr, None) if attr else None

        if _matches(actual, op.value):
            results.append(OperationResult(op, "applied"))
        else:
            results.append(OperationResult(
                op, "unverified", f"expected {op.value!r}, found {actual!r}"
            ))

    return results


def _matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return bool(actual) is expected
    if isinstance(expected, str) and isinstance(actual, str):
        return actual.strip().lower() == expected.strip().lower()
    return actual == expected
