"""Measure and calculation checks: implicit measures, time intelligence, duplicates, hidden helpers."""

from __future__ import annotations

import re

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity

TIME_INTELLIGENCE_FUNCTIONS = re.compile(
    r"\b(TOTALYTD|TOTALQTD|TOTALMTD|SAMEPERIODLASTYEAR|DATEADD|DATESYTD|PARALLELPERIOD|PREVIOUSMONTH|PREVIOUSQUARTER|PREVIOUSYEAR)\b",
    re.IGNORECASE,
)

# DAX pattern checks from org standards
UNQUALIFIED_COLUMN_REF = re.compile(r"(?<!')\[(?!@)[A-Za-z_]\w*\]")
SHORTENED_CALCULATE = re.compile(r"\[[\w\s]+\]\s*\(")
NESTED_IF = re.compile(r"\bIF\s*\(.*\bIF\s*\(", re.IGNORECASE | re.DOTALL)
IFERROR_USAGE = re.compile(r"\bIFERROR\s*\(", re.IGNORECASE)
DIVISION_OPERATOR = re.compile(r"(?<!\w)/(?!\*)")
DIRECT_MEASURE_REF = re.compile(r"^\s*\[[\w\s]+\]\s*$")
MEASURE_TABLE_PATTERN = re.compile(r"^(measures?|_measures?|metrics?)", re.IGNORECASE)


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    all_measures: list[tuple[str, str, str]] = []  # (table, name, expression)
    has_date_table = False
    has_time_intelligence = False

    for table in model.tables:
        # Detect date tables by convention
        table_lower = table.name.lower()
        if "date" in table_lower or "calendar" in table_lower:
            has_date_table = True

        for measure in table.measures:
            all_measures.append((table.name, measure.name, measure.expression))

            if TIME_INTELLIGENCE_FUNCTIONS.search(measure.expression):
                has_time_intelligence = True

            # Hidden helper measures that are still visible
            if not measure.is_hidden and measure.name.startswith("_"):
                findings.append(Finding(
                    category=Category.MEASURES,
                    check="helper_measures_exposed",
                    severity=Severity.MEDIUM,
                    object=f"{table.name}.{measure.name}",
                    object_type=ObjectType.MEASURE,
                    message=f"Measure '{measure.name}' starts with '_' suggesting it's a helper, but it is not hidden.",
                    auto_fixable=True,
                ))

    # Flag models with date tables but no time intelligence
    if has_date_table and not has_time_intelligence and all_measures:
        findings.append(Finding(
            category=Category.MEASURES,
            check="time_intelligence",
            severity=Severity.MEDIUM,
            object="model",
            object_type=ObjectType.MODEL,
            message="Model has a date table but no time intelligence measures (TOTALYTD, SAMEPERIODLASTYEAR, etc.).",
            auto_fixable=False,
        ))

    # Duplicate / overlapping measure names
    name_map: dict[str, list[str]] = {}
    for table, name, _ in all_measures:
        normalized = re.sub(r"[^a-z0-9]", "", name.lower())
        name_map.setdefault(normalized, []).append(f"{table}.{name}")
    for normalized, refs in name_map.items():
        if len(refs) > 1:
            findings.append(Finding(
                category=Category.MEASURES,
                check="duplicate_measures",
                severity=Severity.HIGH,
                object=refs[0],
                object_type=ObjectType.MEASURE,
                message=f"Possibly duplicate measures: {', '.join(refs)}.",
                auto_fixable=False,
            ))

    # Measures not in dedicated measure tables (per org standard: DAX > measure tables)
    tables_with_measures_and_columns = []
    for table in model.tables:
        if table.measures and table.columns:
            if not MEASURE_TABLE_PATTERN.match(table.name):
                tables_with_measures_and_columns.append(table.name)
    if tables_with_measures_and_columns:
        for tname in tables_with_measures_and_columns:
            findings.append(Finding(
                category=Category.MEASURES,
                check="measure_table_required",
                severity=Severity.MEDIUM,
                object=tname,
                object_type=ObjectType.TABLE,
                message=f"Table '{tname}' contains both columns and measures. Per org standard (DAX): store all measures in dedicated measure tables.",
                recommendation="Move measures to a dedicated measure table (e.g., '_Measures').",
                auto_fixable=False,
            ))

    # DAX pattern checks on each measure expression
    for table, name, expression in all_measures:
        qualified_name = f"{table}.{name}"

        # Direct reference measures: measure = [OtherMeasure]
        if DIRECT_MEASURE_REF.match(expression):
            findings.append(Finding(
                category=Category.MEASURES,
                check="direct_measure_reference",
                severity=Severity.LOW,
                object=qualified_name,
                object_type=ObjectType.MEASURE,
                message=f"Measure '{name}' is a direct reference to another measure. Per org standard (DAX): measures should not be direct references of other measures.",
                recommendation="Use measure branching or redefine the calculation.",
                auto_fixable=False,
            ))

        # Skip further DAX checks if expression is very short or empty
        if len(expression.strip()) < 3:
            continue

        # Unqualified column references (per org standard: DAX > fully qualified)
        # Only flag [ColumnName] that isn't preceded by a table name with quotes
        unqualified_refs = UNQUALIFIED_COLUMN_REF.findall(expression)
        if unqualified_refs:
            # Filter out known measure references (measures don't need table qualification)
            measure_names_set = {m[1] for m in all_measures}
            col_refs = [r for r in unqualified_refs if r.strip("[]") not in measure_names_set]
            if col_refs:
                findings.append(Finding(
                    category=Category.MEASURES,
                    check="fully_qualified_columns",
                    severity=Severity.MEDIUM,
                    object=qualified_name,
                    object_type=ObjectType.MEASURE,
                    message=f"Measure '{name}' contains unqualified column references: {', '.join(col_refs[:3])}. Per org standard (DAX): always use fully qualified column references ('Table'[Column]).",
                    recommendation="Use 'TableName'[ColumnName] syntax for all column references.",
                    auto_fixable=False,
                ))

        # Shortened CALCULATE syntax: [measure](filter)
        if SHORTENED_CALCULATE.search(expression):
            findings.append(Finding(
                category=Category.MEASURES,
                check="shortened_calculate",
                severity=Severity.MEDIUM,
                object=qualified_name,
                object_type=ObjectType.MEASURE,
                message=f"Measure '{name}' uses shortened CALCULATE syntax. Per org standard (DAX): use CALCULATE([measure], filter) instead of [measure](filter).",
                recommendation="Replace [measure](filter) with CALCULATE([measure], filter).",
                auto_fixable=False,
            ))

        # IFERROR usage (per org standard: DAX > avoid IFERROR)
        if IFERROR_USAGE.search(expression):
            findings.append(Finding(
                category=Category.MEASURES,
                check="iferror_usage",
                severity=Severity.LOW,
                object=qualified_name,
                object_type=ObjectType.MEASURE,
                message=f"Measure '{name}' uses IFERROR. Per org standard (DAX): avoid IFERROR as it masks errors and hurts performance.",
                recommendation="Handle specific error conditions explicitly instead of using IFERROR.",
                auto_fixable=False,
            ))

        # Nested IF statements (per org standard: DAX > use SWITCH TRUE)
        if NESTED_IF.search(expression):
            findings.append(Finding(
                category=Category.MEASURES,
                check="nested_if",
                severity=Severity.LOW,
                object=qualified_name,
                object_type=ObjectType.MEASURE,
                message=f"Measure '{name}' uses nested IF statements. Per org standard (DAX): use SWITCH(TRUE(), ...) instead of nested IFs.",
                recommendation="Refactor nested IF statements to use SWITCH(TRUE(), condition1, result1, ...).",
                auto_fixable=False,
            ))

        # Division using / operator instead of DIVIDE (per org standard: DAX > use DIVIDE)
        if DIVISION_OPERATOR.search(expression) and "divide" not in expression.lower():
            findings.append(Finding(
                category=Category.MEASURES,
                check="use_divide_function",
                severity=Severity.LOW,
                object=qualified_name,
                object_type=ObjectType.MEASURE,
                message=f"Measure '{name}' uses the / operator for division. Per org standard (DAX): use the DIVIDE function for safe division.",
                recommendation="Replace a / b with DIVIDE(a, b) to handle divide-by-zero gracefully.",
                auto_fixable=False,
            ))

    return findings
