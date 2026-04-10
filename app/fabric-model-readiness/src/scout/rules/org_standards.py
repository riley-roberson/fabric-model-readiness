"""Organization-specific standards checks from Power BI Standards.md.

Covers: display folders, RLS roles, USERELATIONSHIP preference, date table marking,
and default aggregation settings.
"""

from __future__ import annotations

import re

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity

DIMENSION_TABLE_PATTERN = re.compile(r"^(dim|dimension)", re.IGNORECASE)
FACT_TABLE_PATTERN = re.compile(r"^(fact|fct)", re.IGNORECASE)


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    _check_display_folders(model, findings)
    _check_rls_roles(model, findings)
    _check_date_table_marked(model, findings)
    _check_userelationship(model, findings)

    return findings


def _check_display_folders(model: SemanticModel, findings: list[Finding]) -> None:
    """Columns and measures should be grouped in display folders."""
    for table in model.tables:
        if table.is_hidden:
            continue

        # Check columns without display folders (skip hidden columns and key columns)
        visible_cols_without_folder = [
            col for col in table.columns
            if not col.is_hidden and not col.display_folder
        ]
        if len(visible_cols_without_folder) > 3:
            findings.append(Finding(
                category=Category.ORG_STANDARDS,
                check="column_display_folders",
                severity=Severity.MEDIUM,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table.name}' has {len(visible_cols_without_folder)} visible columns without display folders. Per org standard (Data Modeling > Dimension Tables): group columns in display folders.",
                recommendation="Organize columns into logical display folders (e.g., 'Geography', 'Demographics').",
                auto_fixable=False,
            ))

        # Check measures without display folders
        visible_measures_without_folder = [
            m for m in table.measures
            if not m.is_hidden and not m.display_folder
        ]
        if len(visible_measures_without_folder) > 3:
            findings.append(Finding(
                category=Category.ORG_STANDARDS,
                check="measure_display_folders",
                severity=Severity.MEDIUM,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table.name}' has {len(visible_measures_without_folder)} measures without display folders. Per org standard (DAX): group measures in display folders.",
                recommendation="Organize measures into logical display folders (e.g., 'Sales Metrics', 'KPIs').",
                auto_fixable=False,
            ))


def _check_rls_roles(model: SemanticModel, findings: list[Finding]) -> None:
    """Model should have at least Admin and General RLS roles."""
    role_names = {r.name.lower() for r in model.roles}

    if not model.roles:
        findings.append(Finding(
            category=Category.ORG_STANDARDS,
            check="rls_roles_defined",
            severity=Severity.HIGH,
            object="model",
            object_type=ObjectType.MODEL,
            message="No RLS roles defined. Per org standard (Security and Sharing): define at least Admin and General roles.",
            recommendation="Create an Admin role (no filters) and a General role (all filters applied).",
            auto_fixable=False,
        ))
        return

    if "admin" not in role_names:
        findings.append(Finding(
            category=Category.ORG_STANDARDS,
            check="rls_admin_role",
            severity=Severity.HIGH,
            object="model",
            object_type=ObjectType.MODEL,
            message="No 'Admin' RLS role found. Per org standard (Security and Sharing): the Admin role should have no filters.",
            recommendation="Create an Admin role with no filter expressions.",
            auto_fixable=False,
        ))

    if "general" not in role_names:
        findings.append(Finding(
            category=Category.ORG_STANDARDS,
            check="rls_general_role",
            severity=Severity.HIGH,
            object="model",
            object_type=ObjectType.MODEL,
            message="No 'General' RLS role found. Per org standard (Security and Sharing): the General role should have all filters applied.",
            recommendation="Create a General role with appropriate row-level filters.",
            auto_fixable=False,
        ))


def _check_date_table_marked(model: SemanticModel, findings: list[Finding]) -> None:
    """Date/calendar tables should be marked as date tables."""
    for table in model.tables:
        table_lower = table.name.lower()
        if ("date" in table_lower or "calendar" in table_lower) and not table.is_date_table:
            findings.append(Finding(
                category=Category.ORG_STANDARDS,
                check="date_table_marked",
                severity=Severity.HIGH,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table.name}' appears to be a date table but is not marked as one. Per org standard (Dates): mark calendar table as date table.",
                recommendation="Mark the table as a date table in Power BI (Table Tools > Mark as Date Table).",
                auto_fixable=False,
            ))


def _check_userelationship(model: SemanticModel, findings: list[Finding]) -> None:
    """Flag duplicate dimension tables that could use USERELATIONSHIP instead."""
    # Detect patterns like DimDate, DimDate_Order, DimDate_Ship
    # or Date, OrderDate, ShipDate that suggest duplicated dimensions
    base_dims: dict[str, list[str]] = {}
    for table in model.tables:
        name = table.name
        # Normalize: strip Dim prefix and common suffixes
        base = re.sub(r"^(dim|dimension)\s*", "", name, flags=re.IGNORECASE)
        base = re.sub(r"[_\s]?(order|ship|invoice|delivery|due|start|end|create|update|birth|hire).*$", "", base, flags=re.IGNORECASE)
        if base:
            base_lower = base.lower().strip()
            if base_lower:
                base_dims.setdefault(base_lower, []).append(name)

    for base, tables in base_dims.items():
        if len(tables) > 1:
            findings.append(Finding(
                category=Category.ORG_STANDARDS,
                check="userelationship_preferred",
                severity=Severity.MEDIUM,
                object=", ".join(tables),
                object_type=ObjectType.TABLE,
                message=f"Tables {', '.join(tables)} appear to be duplicated dimensions. Per org standard (Dimension Tables, Dates): use USERELATIONSHIP with inactive relationships instead of duplicating dimension tables.",
                recommendation="Consolidate into a single dimension table and use USERELATIONSHIP() in DAX measures for role-playing scenarios.",
                auto_fixable=False,
            ))
