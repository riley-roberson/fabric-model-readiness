"""Turn findings into concrete, applyable model edits.

Only a subset of checks can be fixed mechanically. A missing description can be
written; a pivoted table cannot be unpivoted by setting a property. Anything not
in CHECK_OPERATIONS is reported as unsupported rather than silently dropped, so
the caller can tell "we chose not to" from "we forgot".

Property names are the MCP's, verified against the running server: `isHidden`,
`dataCategory`, `summarizeBy`, `sortByColumn`, `displayFolder`, `defaultLabel`,
`description`, `dataType`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from shared.model import Finding, ObjectType, SemanticModel

# check -> (object kind, MCP property, value resolver name)
CHECK_OPERATIONS: dict[str, tuple[str, str, str]] = {
    # Metadata
    "table_descriptions": ("table", "description", "description"),
    "column_descriptions": ("column", "description", "description"),
    "measure_descriptions": ("measure", "description", "description"),
    "data_categories": ("column", "dataCategory", "data_category"),
    "row_label_defined": ("column", "defaultLabel", "true"),
    # Visibility
    "fact_table_hidden": ("table", "isHidden", "true"),
    "surrogate_key_hidden": ("column", "isHidden", "true"),
    "unnecessary_columns": ("column", "isHidden", "true"),
    "noise_fields_excluded": ("column", "isHidden", "true"),
    "helper_measures_exposed": ("measure", "isHidden", "true"),
    # Aggregation and typing
    "default_summarization": ("column", "summarizeBy", "none"),
    "explicit_measures": ("column", "summarizeBy", "none"),
    "incorrect_data_types": ("column", "dataType", "data_type"),
}

GEOGRAPHY_CATEGORIES = [
    (re.compile(r"\b(postal|zip)\b", re.I), "PostalCode"),
    (re.compile(r"\bcountry\b", re.I), "Country"),
    (re.compile(r"\b(state|province)\b", re.I), "StateOrProvince"),
    (re.compile(r"\bcity\b", re.I), "City"),
    (re.compile(r"\bcounty\b", re.I), "County"),
    (re.compile(r"\blatitude\b", re.I), "Latitude"),
    (re.compile(r"\blongitude\b", re.I), "Longitude"),
    (re.compile(r"\b(address|street)\b", re.I), "Address"),
    (re.compile(r"\bcontinent\b", re.I), "Continent"),
    (re.compile(r"\bregion\b", re.I), "Place"),
]

DATE_NAME = re.compile(r"(^|[\s_])(date|datetime|timestamp)([\s_]|$)|date$", re.I)

# The column that names an entity: "Customer Name", "Product Title".
LABEL_COLUMN = re.compile(r"(^|[\s_])(name|title|label|description)([\s_]|$)|name$", re.I)
TEXT_TYPES = {"string", "text"}


@dataclass
class ChangeOperation:
    """One property write against one model object."""

    finding_id: str
    check: str
    kind: str          # table | column | measure
    table: str
    name: str          # "" for table-level
    prop: str
    value: Any
    before: Any = None

    @property
    def target(self) -> str:
        return f"{self.table}.{self.name}" if self.name else self.table

    def describe(self) -> str:
        return f"{self.target}: {self.prop} = {self.value!r}"

    def to_definition(self) -> dict:
        """The MCP `definitions[]` entry for this write."""
        if self.kind == "table":
            return {"name": self.table, self.prop: self.value}
        return {"tableName": self.table, "name": self.name, self.prop: self.value}


@dataclass
class UnsupportedChange:
    finding_id: str
    check: str
    object: str
    reason: str


def split_object(finding: Finding) -> tuple[str, str]:
    """Split a finding's object into (table, name).

    Table names can themselves contain dots, so trust object_type first and only
    fall back to splitting when the finding really is column- or measure-level.
    """
    if finding.object_type == ObjectType.TABLE:
        return finding.object, ""
    table, _, name = finding.object.partition(".")
    return table, name


def build_operations(
    model: SemanticModel,
    findings: list[Finding],
    values: dict[str, Any] | None = None,
) -> tuple[list[ChangeOperation], list[UnsupportedChange]]:
    """Map accepted findings onto concrete writes.

    `values` supplies caller-provided text (edited descriptions, for example)
    keyed by finding id, and takes precedence over anything generated here.
    """
    values = values or {}
    operations: list[ChangeOperation] = []
    unsupported: list[UnsupportedChange] = []

    index = _ModelIndex(model)

    for finding in findings:
        mapping = CHECK_OPERATIONS.get(finding.check)
        if mapping is None:
            unsupported.append(UnsupportedChange(
                finding_id=finding.id,
                check=finding.check,
                object=finding.object,
                reason="No mechanical fix exists for this check; it needs a modelling decision.",
            ))
            continue

        kind, prop, resolver = mapping
        table, name = split_object(finding)

        # row_label_defined is reported against the table, but the write lands on
        # whichever column names the entity. That is a modelling decision, so it
        # is only made automatically when exactly one column is an obvious fit.
        if finding.check == "row_label_defined":
            candidates = index.label_candidates(table)
            if len(candidates) != 1:
                unsupported.append(UnsupportedChange(
                    finding_id=finding.id,
                    check=finding.check,
                    object=finding.object,
                    reason=(
                        f"{len(candidates)} columns could serve as the row label"
                        f"{' (' + ', '.join(candidates[:4]) + ')' if candidates else ''}"
                        " -- pick one rather than have it guessed."
                    ),
                ))
                continue
            name = candidates[0]

        value = values.get(finding.id)
        if value is None:
            value = _resolve_value(resolver, finding, table, name, index)

        if value is None:
            unsupported.append(UnsupportedChange(
                finding_id=finding.id,
                check=finding.check,
                object=finding.object,
                reason="Could not derive a safe value automatically; supply one explicitly.",
            ))
            continue

        operations.append(ChangeOperation(
            finding_id=finding.id,
            check=finding.check,
            kind=kind,
            table=table,
            name=name,
            prop=prop,
            value=value,
            before=index.current(kind, table, name, prop),
        ))

    return operations, unsupported


def _resolve_value(
    resolver: str, finding: Finding, table: str, name: str, index: _ModelIndex
) -> Any:
    if resolver == "true":
        return True
    if resolver == "none":
        return "none"
    if resolver == "data_category":
        return _geography_category(name)
    if resolver == "data_type":
        return "dateTime" if DATE_NAME.search(name) else "double"
    if resolver == "description":
        # Generated text is the caller's job -- see enforcer.planner and
        # shared.llm. Refusing here keeps a placeholder out of the model.
        return None
    return None


def _geography_category(column_name: str) -> str | None:
    for pattern, category in GEOGRAPHY_CATEGORIES:
        if pattern.search(column_name):
            return category
    return None


class _ModelIndex:
    """Lookup for current property values, so changes record a `before`."""

    def __init__(self, model: SemanticModel):
        self._tables = {t.name: t for t in model.tables}
        self._columns = {
            (t.name, c.name): c for t in model.tables for c in t.columns
        }
        self._measures = {
            (t.name, m.name): m for t in model.tables for m in t.measures
        }

    def label_candidates(self, table_name: str) -> list[str]:
        """Visible text columns that plausibly name the entity."""
        table = self._tables.get(table_name)
        if table is None:
            return []
        return [
            c.name for c in table.columns
            if not c.is_hidden
            and c.data_type.lower() in TEXT_TYPES
            and LABEL_COLUMN.search(c.name)
        ]

    def current(self, kind: str, table: str, name: str, prop: str) -> Any:
        obj = None
        if kind == "table":
            obj = self._tables.get(table)
        elif kind == "column":
            obj = self._columns.get((table, name))
        elif kind == "measure":
            obj = self._measures.get((table, name))
        if obj is None:
            return None

        attr = {
            "description": "description",
            "isHidden": "is_hidden",
            "dataCategory": "data_category",
            "summarizeBy": "summarize_by",
            "sortByColumn": "sort_by_column",
            "displayFolder": "display_folder",
            "defaultLabel": "is_default_label",
            "dataType": "data_type",
        }.get(prop)
        return getattr(obj, attr, None) if attr else None
