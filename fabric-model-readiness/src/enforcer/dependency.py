"""Dependency analysis: trace DAX measure references before hiding/removing objects."""

from __future__ import annotations

import re

from shared.model import SemanticModel


def find_dependents(model: SemanticModel, target_object: str) -> list[str]:
    """Find all visible measures that reference the target column or table.

    Args:
        model: The parsed semantic model.
        target_object: A qualified name like 'TableName.ColumnName' or just 'TableName'.

    Returns:
        List of measure names (qualified as Table.Measure) that reference the target.
    """
    dependents: list[str] = []
    parts = target_object.split(".")
    table_name = parts[0]
    column_name = parts[1] if len(parts) > 1 else None

    for table in model.tables:
        for measure in table.measures:
            if measure.is_hidden:
                continue
            if _references_object(measure.expression, table_name, column_name):
                dependents.append(f"{table.name}.{measure.name}")

    return dependents


def _references_object(dax_expression: str, table_name: str, column_name: str | None) -> bool:
    """Check if a DAX expression references a table or column.

    Handles common DAX reference patterns:
        - 'TableName'[ColumnName]
        - [ColumnName] (unqualified)
        - RELATED(TableName[ColumnName])
        - TableName[ColumnName] without quotes
    """
    if not dax_expression:
        return False

    # Table reference
    if re.search(rf"(?i)\b{re.escape(table_name)}\b", dax_expression):
        if column_name is None:
            return True
        # Column reference within table context
        if re.search(rf"(?i)\[{re.escape(column_name)}\]", dax_expression):
            return True

    # Unqualified column reference
    if column_name and re.search(rf"(?i)\[{re.escape(column_name)}\]", dax_expression):
        return True

    return False


def safe_to_hide(model: SemanticModel, target_object: str) -> tuple[bool, list[str]]:
    """Check if it's safe to hide an object from the AI schema.

    Returns:
        (is_safe, list_of_blocking_measures)
    """
    dependents = find_dependents(model, target_object)
    return (len(dependents) == 0, dependents)
