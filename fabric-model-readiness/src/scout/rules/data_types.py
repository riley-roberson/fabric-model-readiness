"""Data type and aggregation checks: correct types, default summarization, sort-by-column."""

from __future__ import annotations

import re

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity

NO_SUMMARIZE_KEYWORDS = {"year", "month", "day", "id", "age", "code", "number", "key"}


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    for table in model.tables:
        for col in table.columns:
            col_lower = col.name.lower()

            # Default summarization: flag SUM on year/month/day/id/age columns
            should_not_sum = any(kw in col_lower for kw in NO_SUMMARIZE_KEYWORDS)
            if should_not_sum and col.summarize_by.lower() in ("sum", ""):
                # Empty summarize_by defaults to SUM in Power BI for numeric types
                if col.data_type.lower() in ("int64", "double", "decimal", "whole number", "decimal number"):
                    findings.append(Finding(
                        category=Category.DATA_TYPES,
                        check="default_summarization",
                        severity=Severity.HIGH,
                        object=f"{table.name}.{col.name}",
                        object_type=ObjectType.COLUMN,
                        message=f"Column '{col.name}' should use 'Don't Summarize' instead of SUM.",
                        auto_fixable=True,
                    ))

            # Sort By Column for month/day name columns
            is_name_col = re.search(r"(month|day)\s*(name|label)", col_lower)
            if is_name_col and not col.sort_by_column:
                findings.append(Finding(
                    category=Category.DATA_TYPES,
                    check="sort_by_column",
                    severity=Severity.LOW,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=f"Column '{col.name}' appears to be a name field that needs Sort By Column configured for correct ordering.",
                    auto_fixable=True,
                ))

            # Float data types (per org standard: Data Modeling > General)
            if col.data_type.lower() in ("double", "single"):
                findings.append(Finding(
                    category=Category.DATA_TYPES,
                    check="avoid_float_types",
                    severity=Severity.MEDIUM,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=f"Column '{col.name}' uses float type '{col.data_type}'. Per org standard (Data Modeling > General): avoid float data types unless necessary. Use Decimal Number instead.",
                    recommendation="Change data type to Decimal (fixed decimal number) for financial/exact data.",
                    auto_fixable=False,
                ))

    return findings
