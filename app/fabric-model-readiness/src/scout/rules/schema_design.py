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

# A denormalized island: enough columns to be a real table, no relationships.
DENORMALIZED_COLUMN_THRESHOLD = 10

# Column headers that are data values -- the signature of a pivoted source.
PIVOTED_COLUMN = re.compile(
    r"^((19|20)\d{2}|q[1-4]|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"([\s_-]?((19|20)\d{2}|\d{1,2}))?$",
    re.IGNORECASE,
)
PIVOTED_THRESHOLD = 3

# Truncated tokens that read as technical shorthand rather than business
# language. The checklist calls these out by example: TR_AMT, CustName.
ABBREVIATION_TOKENS = {
    "cust", "qty", "amt", "nbr", "num", "desc", "addr", "txn", "trx", "mgr",
    "dept", "acct", "invc", "ord", "prod", "cat", "grp", "val", "pct", "tot",
    "emp", "vend", "whs", "loc", "seq", "flg", "ind", "src", "tgt", "curr",
    "prev", "yr", "mo", "wk", "lvl", "typ", "nm", "dt", "cd", "org", "chg",
}

# Technical and audit columns that carry no business meaning for an agent.
HOUSEKEEPING_COLUMN = re.compile(
    r"^(etl|dw|dwh|stg|staging|sys)[\s_]"
    r"|[\s_](etl|batch|checksum|hash|rowversion|lineage)[\s_]?"
    r"|^(created|modified|updated|inserted|loaded)[\s_]?(by|on|at|date|time|ts)?$"
    r"|^(is[\s_]?(deleted|current)|valid[\s_]?(from|to)|effective[\s_]?(from|to)"
    r"|source[\s_]?system|record[\s_]?source|load[\s_]?(date|time|id))$",
    re.IGNORECASE,
)

_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_TOKEN_SPLIT = re.compile(r"[\s_\-.]+")
_VOWEL = re.compile(r"[aeiouy]", re.IGNORECASE)


def _tokenize(name: str) -> list[str]:
    """Split a name into word tokens across spaces, underscores, and camelCase
    boundaries, so "TR_AMT" and "CustName" both decompose.
    """
    spaced = _CAMEL_BOUNDARY.sub(r"\1 \2", name)
    return [t for t in _TOKEN_SPLIT.split(spaced) if t]


def _is_cryptic_token(token: str) -> bool:
    """True when a token reads as shorthand: a known abbreviation or vowel-less."""
    if token.lower() in ABBREVIATION_TOKENS:
        return True
    return 3 <= len(token) <= 6 and not _VOWEL.search(token)


def _cryptic_tokens_in(name: str) -> list[str]:
    return [t for t in _tokenize(name) if _is_cryptic_token(t)]


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    # Tables already reported as pivoted, so they are not reported twice.
    pivoted_tables: set[str] = set()

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

        # Cryptic table names ("Use clear, business-friendly names")
        table_cryptic = _cryptic_tokens_in(table.name)
        if table_cryptic and not table.is_hidden:
            findings.append(Finding(
                category=Category.SCHEMA_DESIGN,
                check="business_friendly_names",
                severity=Severity.MEDIUM,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=(
                    f"Table '{table.name}' uses shorthand ({', '.join(table_cryptic)}). Agents "
                    "match on names, so spell them the way users say them."
                ),
                recommendation="Rename to the full business term, e.g. 'Cust' becomes 'Customer'.",
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

            if col.is_hidden:
                continue

            col_cryptic = _cryptic_tokens_in(col.name)
            if col_cryptic:
                findings.append(Finding(
                    category=Category.SCHEMA_DESIGN,
                    check="business_friendly_names",
                    severity=Severity.MEDIUM,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=(
                        f"Column '{col.name}' uses shorthand ({', '.join(col_cryptic)}) rather "
                        "than business language."
                    ),
                    recommendation="Rename to the full business term, e.g. 'TR_AMT' becomes 'Transaction Amount'.",
                ))

            # Housekeeping columns the agent has no use for
            if HOUSEKEEPING_COLUMN.search(col.name):
                findings.append(Finding(
                    category=Category.SCHEMA_DESIGN,
                    check="unnecessary_columns",
                    severity=Severity.MEDIUM,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=(
                        f"Column '{col.name}' looks like an audit or ETL column. It adds noise to "
                        "the AI schema without answering business questions."
                    ),
                    recommendation="Remove the column from the model, or hide it so it stays out of the AI data schema.",
                    auto_fixable=True,
                ))

        # Pivoted structures: data values used as column headers
        pivoted = [c for c in table.columns if PIVOTED_COLUMN.match(c.name.strip())]
        if len(pivoted) >= PIVOTED_THRESHOLD:
            pivoted_tables.add(table.name)
            sample = ", ".join(c.name for c in pivoted[:3])
            findings.append(Finding(
                category=Category.SCHEMA_DESIGN,
                check="star_schema_structure",
                severity=Severity.HIGH,
                object=table.name,
                object_type=ObjectType.TABLE,
                message=(
                    f"Table '{table.name}' has {len(pivoted)} columns named after data values "
                    f"({sample}...). This is a pivoted structure, which agents cannot aggregate over."
                ),
                recommendation="Unpivot these columns into a single attribute column plus a value column.",
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

            measure_cryptic = _cryptic_tokens_in(measure.name)
            if measure_cryptic and not measure.is_hidden:
                findings.append(Finding(
                    category=Category.SCHEMA_DESIGN,
                    check="business_friendly_names",
                    severity=Severity.MEDIUM,
                    object=f"{table.name}.{measure.name}",
                    object_type=ObjectType.MEASURE,
                    message=(
                        f"Measure '{measure.name}' uses shorthand ({', '.join(measure_cryptic)}) "
                        "rather than business language."
                    ),
                    recommendation="Rename to the term users would say out loud.",
                ))

    # Build set of "many-side" tables from relationships (likely fact tables)
    many_side_tables: set[str] = set()
    related_tables: set[str] = set()
    for rel in model.relationships:
        # In TMSL, fromTable is typically the many side
        many_side_tables.add(rel.from_table)
        related_tables.add(rel.from_table)
        related_tables.add(rel.to_table)

    # Flat / denormalized tables: substantial, visible, and joined to nothing
    for table in model.tables:
        if table.is_hidden or table.is_calculation_group or table.is_field_parameter:
            continue
        if table.name in related_tables:
            continue
        if table.name in pivoted_tables:
            continue
        if len(table.columns) < DENORMALIZED_COLUMN_THRESHOLD:
            continue

        findings.append(Finding(
            category=Category.SCHEMA_DESIGN,
            check="star_schema_structure",
            severity=Severity.HIGH,
            object=table.name,
            object_type=ObjectType.TABLE,
            message=(
                f"Table '{table.name}' has {len(table.columns)} columns and no relationships. A "
                "flat, denormalized table gives the agent no fact/dimension structure to reason over."
            ),
            recommendation="Split into a fact table plus conformed dimension tables and relate them in a star schema.",
        ))

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
