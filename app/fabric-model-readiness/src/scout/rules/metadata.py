"""Metadata completeness checks: descriptions, synonyms, data categories."""

from __future__ import annotations

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity

GEOGRAPHY_KEYWORDS = {"city", "state", "country", "zip", "postal", "region", "latitude", "longitude"}


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    _check_row_labels(model, findings)

    for table in model.tables:
        # Table descriptions
        if not table.description.strip():
            findings.append(Finding(
                category=Category.METADATA_COMPLETENESS,
                check="table_descriptions",
                severity=Severity.CRITICAL,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=f"Table '{table.name}' has no description. Copilot uses the first 200 characters of table descriptions to understand purpose.",
                auto_fixable=True,
            ))

        for col in table.columns:
            # Column descriptions
            if not col.is_hidden and not col.description.strip():
                findings.append(Finding(
                    category=Category.METADATA_COMPLETENESS,
                    check="column_descriptions",
                    severity=Severity.HIGH,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=f"Column '{col.name}' in '{table.name}' has no description.",
                    auto_fixable=True,
                ))

            # Data categories for geography columns
            col_lower = col.name.lower()
            if any(kw in col_lower for kw in GEOGRAPHY_KEYWORDS) and not col.data_category:
                findings.append(Finding(
                    category=Category.METADATA_COMPLETENESS,
                    check="data_categories",
                    severity=Severity.MEDIUM,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=f"Column '{col.name}' looks like a geography field but has no Data Category set.",
                    auto_fixable=True,
                ))

            # Synonyms on key business columns
            if not col.is_hidden and not col.synonyms:
                findings.append(Finding(
                    category=Category.METADATA_COMPLETENESS,
                    check="synonyms",
                    severity=Severity.MEDIUM,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=f"Column '{col.name}' in '{table.name}' has no synonyms for natural language matching.",
                    auto_fixable=True,
                ))

        # Measure descriptions
        for measure in table.measures:
            if not measure.description.strip():
                findings.append(Finding(
                    category=Category.METADATA_COMPLETENESS,
                    check="measure_descriptions",
                    severity=Severity.CRITICAL,
                    object=f"{table.name}.{measure.name}",
                    object_type=ObjectType.MEASURE,
                    message=f"Measure '{measure.name}' has no description explaining what it calculates.",
                    auto_fixable=True,
                ))

    return findings


def _check_row_labels(model: SemanticModel, findings: list[Finding]) -> None:
    """Row labels tell Q&A and Data Agent which column names a row.

    Without one, "show me the top customers" has no obvious column to return.
    The checklist calls this out especially for dimension tables.

    A dimension is a table something else points at. Tables on the many side are
    facts, and disconnected tables are a structural problem already reported by
    star_schema_structure -- neither should be asked for a row label.
    """
    one_side_tables = {r.to_table for r in model.relationships}
    many_side_tables = {r.from_table for r in model.relationships}

    for table in model.tables:
        if table.is_hidden or table.is_calculation_group or table.is_field_parameter:
            continue
        if table.name not in one_side_tables:
            continue
        if table.name in many_side_tables:
            continue
        if len(table.columns) < 2:
            continue
        if any(c.is_default_label for c in table.columns):
            continue

        findings.append(Finding(
            category=Category.METADATA_COMPLETENESS,
            check="row_label_defined",
            severity=Severity.MEDIUM,
            object=table.name,
            object_type=ObjectType.TABLE,
            message=(
                f"Dimension table '{table.name}' has no row label defined. Data Agent has no "
                "designated column to identify a row by."
            ),
            recommendation=(
                "In Power BI Desktop, set the row label to the column that names the entity "
                "(e.g. Customer Name on Customer)."
            ),
            auto_fixable=True,
        ))
