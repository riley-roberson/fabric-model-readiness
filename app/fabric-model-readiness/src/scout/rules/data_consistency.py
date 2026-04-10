"""Data consistency checks: partitioned tables, naming patterns suggesting issues."""

from __future__ import annotations

import re

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    # Detect partitioned tables (Sales2020, Sales2021, etc.)
    year_suffix_groups: dict[str, list[str]] = {}
    for table in model.tables:
        match = re.match(r"^(.+?)(20\d{2})$", table.name)
        if match:
            base = match.group(1)
            year_suffix_groups.setdefault(base, []).append(table.name)

    for base, tables in year_suffix_groups.items():
        if len(tables) > 1:
            findings.append(Finding(
                category=Category.DATA_CONSISTENCY,
                check="partitioned_tables",
                severity=Severity.LOW,
                object=tables[0],
                object_type=ObjectType.TABLE,
                message=f"Tables {', '.join(sorted(tables))} appear to be year-partitioned. Consider unioning into a single table.",
                auto_fixable=False,
            ))

    return findings
