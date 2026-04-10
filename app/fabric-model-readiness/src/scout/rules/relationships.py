"""Relationship checks: orphaned tables, inactive relationships, ambiguous paths, cardinality."""

from __future__ import annotations

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    # Build set of tables that participate in at least one relationship
    connected_tables: set[str] = set()
    for rel in model.relationships:
        connected_tables.add(rel.from_table)
        connected_tables.add(rel.to_table)

    # Orphaned tables
    for table in model.tables:
        if table.name not in connected_tables and not table.is_hidden:
            findings.append(Finding(
                category=Category.RELATIONSHIPS,
                check="missing_relationships",
                severity=Severity.CRITICAL,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table.name}' has no relationships. Copilot cannot traverse disconnected tables.",
                auto_fixable=False,
            ))

    # Inactive relationships
    for rel in model.relationships:
        if not rel.is_active:
            findings.append(Finding(
                category=Category.RELATIONSHIPS,
                check="inactive_relationships",
                severity=Severity.MEDIUM,
                object=f"{rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}",
                object_type=ObjectType.RELATIONSHIP,
                message=f"Inactive relationship between '{rel.from_table}' and '{rel.to_table}'. Consider denormalization if this is a role-playing dimension.",
                auto_fixable=False,
            ))

    # Many-to-many cardinality
    for rel in model.relationships:
        cardinality = rel.cardinality.lower()
        if "many" in cardinality and "many" in cardinality.replace("many", "", 1):
            findings.append(Finding(
                category=Category.RELATIONSHIPS,
                check="cardinality_correctness",
                severity=Severity.HIGH,
                object=f"{rel.from_table} <-> {rel.to_table}",
                object_type=ObjectType.RELATIONSHIP,
                message=f"Many-to-many relationship between '{rel.from_table}' and '{rel.to_table}'. Review for correctness.",
                auto_fixable=False,
            ))

    # Bi-directional relationships (per org standard: Data Modeling > Star Schemas, DAX > CROSSFILTER)
    for rel in model.relationships:
        direction = rel.cross_filter_direction.lower()
        if direction in ("bothdirections", "both"):
            findings.append(Finding(
                category=Category.RELATIONSHIPS,
                check="bidirectional_relationship",
                severity=Severity.HIGH,
                object=f"{rel.from_table} <-> {rel.to_table}",
                object_type=ObjectType.RELATIONSHIP,
                message=f"Bi-directional relationship between '{rel.from_table}' and '{rel.to_table}'. Per org standard (Star Schemas): avoid bi-directional relationships. Use CROSSFILTER in DAX instead.",
                recommendation="Change to single-direction filtering and use CROSSFILTER() in DAX measures where needed.",
                auto_fixable=False,
            ))

    # Ambiguous paths: tables reachable via more than one active relationship path
    active_edges: dict[str, list[str]] = {}
    for rel in model.relationships:
        if rel.is_active:
            active_edges.setdefault(rel.from_table, []).append(rel.to_table)
            active_edges.setdefault(rel.to_table, []).append(rel.from_table)

    for table_name, neighbors in active_edges.items():
        if len(neighbors) != len(set(neighbors)):
            findings.append(Finding(
                category=Category.RELATIONSHIPS,
                check="ambiguous_paths",
                severity=Severity.MEDIUM,
                object=table_name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table_name}' has multiple active relationship paths to the same table.",
                auto_fixable=False,
            ))

    return findings
