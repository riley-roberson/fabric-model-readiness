"""Schema design checks: star schema, naming conventions, wide tables, property bags."""

from __future__ import annotations

import re

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity

BAD_TABLE_NAMES = re.compile(r"^(Table\d+|Sheet\d+|Query\d+)$", re.IGNORECASE)
BAD_COLUMN_NAMES = re.compile(r"^(Col\d+|Field\d+)$", re.IGNORECASE)
ABBREVIATED_PATTERN = re.compile(r"^[A-Z][a-z]{0,2}[A-Z]")
WIDE_TABLE_THRESHOLD = 30
FACT_TABLE_PATTERN = re.compile(r"^(fact|fct)", re.IGNORECASE)
SURROGATE_KEY_PATTERN = re.compile(r"(id|key|sk|fk)$", re.IGNORECASE)


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    for table in model.tables:
        # Bad table names
        if BAD_TABLE_NAMES.match(table.name):
            findings.append(Finding(
                category=Category.SCHEMA_DESIGN,
                check="table_naming",
                severity=Severity.HIGH,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table.name}' uses a generic name. Rename to reflect its business purpose.",
                auto_fixable=False,
            ))

        # Wide tables
        if len(table.columns) >= WIDE_TABLE_THRESHOLD:
            findings.append(Finding(
                category=Category.SCHEMA_DESIGN,
                check="wide_table_detection",
                severity=Severity.MEDIUM,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table.name}' has {len(table.columns)} columns. Consider normalizing or unpivoting.",
                auto_fixable=False,
            ))

        # Bad column names
        for col in table.columns:
            if BAD_COLUMN_NAMES.match(col.name):
                findings.append(Finding(
                    category=Category.SCHEMA_DESIGN,
                    check="column_naming",
                    severity=Severity.HIGH,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=f"Column '{col.name}' in '{table.name}' uses a generic name.",
                    auto_fixable=False,
                ))

        # Bad measure names
        for measure in table.measures:
            if re.match(r"^(M\d+|Calc\d+|Measure\s*\d+)$", measure.name, re.IGNORECASE):
                findings.append(Finding(
                    category=Category.SCHEMA_DESIGN,
                    check="measure_naming",
                    severity=Severity.HIGH,
                    object=f"{table.name}.{measure.name}",
                    object_type=ObjectType.MEASURE,
                    message=f"Measure '{measure.name}' uses a generic name. Rename to reflect its calculation purpose.",
                    auto_fixable=False,
                ))

    # Build set of "many-side" tables from relationships (likely fact tables)
    many_side_tables: set[str] = set()
    for rel in model.relationships:
        # In TMSL, fromTable is typically the many side
        many_side_tables.add(rel.from_table)

    for table in model.tables:
        is_fact = FACT_TABLE_PATTERN.match(table.name) or table.name in many_side_tables

        # Fact tables should be hidden (per org standard: Data Modeling > Fact Tables)
        if is_fact and not table.is_hidden:
            findings.append(Finding(
                category=Category.SCHEMA_DESIGN,
                check="fact_table_hidden",
                severity=Severity.HIGH,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Fact table '{table.name}' is not hidden. Per org standard (Data Modeling > Fact Tables): fact tables should be hidden from users.",
                recommendation="Hide the fact table. Expose only measures and degenerate dimensions.",
                auto_fixable=True,
            ))

        # Surrogate keys should be hidden on dimension tables (per org standard: Data Modeling > Dimension Tables)
        if not is_fact:
            for col in table.columns:
                if SURROGATE_KEY_PATTERN.search(col.name) and not col.is_hidden:
                    findings.append(Finding(
                        category=Category.SCHEMA_DESIGN,
                        check="surrogate_key_hidden",
                        severity=Severity.MEDIUM,
                        object=f"{table.name}.{col.name}",
                        object_type=ObjectType.COLUMN,
                        message=f"Surrogate key '{col.name}' in dimension '{table.name}' is not hidden. Per org standard (Data Modeling > Dimension Tables): hide surrogate keys from users.",
                        recommendation="Set isHidden=true on the surrogate key column.",
                        auto_fixable=True,
                    ))

    # Cross-table column name duplicates
    col_names: dict[str, list[str]] = {}
    for table in model.tables:
        for col in table.columns:
            col_names.setdefault(col.name, []).append(table.name)
    for name, tables in col_names.items():
        if len(tables) > 1:
            findings.append(Finding(
                category=Category.SCHEMA_DESIGN,
                check="cross_table_disambiguation",
                severity=Severity.MEDIUM,
                object=name,
                object_type=ObjectType.COLUMN,
                message=f"Column '{name}' appears in tables: {', '.join(tables)}. Disambiguate to avoid Copilot confusion.",
                auto_fixable=False,
            ))

    return findings
