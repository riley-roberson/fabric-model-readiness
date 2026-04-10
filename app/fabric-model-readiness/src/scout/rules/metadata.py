"""Metadata completeness checks: descriptions, synonyms, data categories."""

from __future__ import annotations

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity

GEOGRAPHY_KEYWORDS = {"city", "state", "country", "zip", "postal", "region", "latitude", "longitude"}


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

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
