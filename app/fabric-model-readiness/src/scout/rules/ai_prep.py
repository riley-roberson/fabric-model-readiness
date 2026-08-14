"""Prep for AI checks, derived from the Microsoft "Semantic Model Preparation
Checklist for Fabric Data Agent".

Covers the three model-side sections of that checklist:
  - AI Data Schema   (Prep for AI > Simplify data schema)
  - Verified Answers (Prep for AI > Verified answers)
  - AI Instructions  (Prep for AI > Add AI instructions)

Checklist items that cannot be observed in a .SemanticModel folder (portal
configuration, notebook runs, Data Agent setup, live testing) are carried in
scout/checklist.py instead and are not scored.

Kept deliberately in step with docs/src/scanner/rules/aiPrep.ts -- the two
implementations are held together by tests/test_scout_rules/test_check_parity.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from shared.model import (
    Category,
    Finding,
    ObjectType,
    SemanticModel,
    Severity,
    TableInfo,
)

# Column-name shapes that should stay out of the AI schema.
#
# Matched against name *tokens* rather than a raw suffix regex. An earlier
# suffix pattern anchored on (^|[\s_]) to avoid firing on words that merely end
# in a noise substring ("Valid", "Paid", "Monkey"), but that also meant it only
# saw separated forms -- "Customer ID" matched while the far more common
# "CustomerID" did not. Tokenizing on camelCase boundaries catches both without
# reintroducing the false positives.
NOISE_TOKENS = {
    "id", "ids", "key", "keys", "sk", "fk", "guid", "uid", "idx", "index",
    "sort", "sortorder", "ordinal", "rowversion", "hash",
}
NOISE_PREFIXES = re.compile(r"^(sk|fk|pk|idx)([\s_]|$)", re.IGNORECASE)

_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_TOKEN_SPLIT = re.compile(r"[\s_\-.]+")


def _name_tokens(name: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(_CAMEL_BOUNDARY.sub(r"\1 \2", name)) if t]


def is_noise_column_name(name: str) -> bool:
    """True when a column name reads as a key, index, or sort helper."""
    name = name.strip()
    if NOISE_PREFIXES.search(name):
        return True

    tokens = [t.lower() for t in _name_tokens(name)]
    if not tokens:
        return False
    if tokens[-1] in NOISE_TOKENS:
        return True
    # Two-word forms that are only noise when joined: "Sort Order", "SortOrder".
    return len(tokens) >= 2 and (tokens[-2] + tokens[-1]) in NOISE_TOKENS

# Names suggesting a helper or intermediate calculation, not a reportable metric.
HELPER_MEASURE = re.compile(
    r"^(_|tmp|temp|test|helper|aux|base|calc)|(\b(helper|temp|internal|scratch|do not use|dnu)\b)",
    re.IGNORECASE,
)

DATE_COLUMN = re.compile(r"\b(date|datetime|timestamp)\b|date$", re.IGNORECASE)

_DATE_TYPE = re.compile(r"date|time", re.IGNORECASE)

INSTRUCTIONS_OBJECT = "Copilot/Instructions/instructions.md"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []

    _check_ai_data_schema(model, findings)
    _check_verified_answers(model, findings)
    _check_ai_instructions(model, findings)

    # Deliberately outside _check_ai_data_schema: a verified answer pointing at a
    # hidden column fails whether or not a Prep for AI schema has been configured,
    # and that function returns early when schema.json is absent.
    if model.copilot.verified_answers and model.tables:
        _check_hidden_field_conflicts(model, findings)

    return findings


# ---------------------------------------------------------------------------
# AI Data Schema (Prep for AI > Simplify data schema)
# ---------------------------------------------------------------------------

def _check_ai_data_schema(model: SemanticModel, findings: list[Finding]) -> None:
    copilot = model.copilot

    if not copilot.schema_json_exists:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_schema_configured",
            severity=Severity.CRITICAL,
            object="Copilot/schema.json",
            object_type=ObjectType.COPILOT_SCHEMA,
            message=(
                "AI data schema (Copilot/schema.json) is missing entirely. Data Agent uses "
                "the Prep for AI schema to decide which tables, columns, and measures it may query."
            ),
            recommendation="Open the model in Power BI Desktop and configure Prep for AI > Simplify data schema.",
        ))
        # Every remaining schema check reads the selection -- nothing to read.
        return

    selection = _extract_selection(copilot.schema_json)

    # "Select only relevant tables, columns, and measures (very important)"
    _check_schema_scope(model, selection, findings)

    # "Include all dependent objects for selected measures"
    _check_schema_dependencies(model, selection, findings)

    # "Exclude helper measures and intermediate calculation objects"
    _check_schema_helper_objects(model, selection, findings)

    # "Exclude duplicate or overlapping measures"
    _check_schema_duplicate_measures(model, selection, findings)

    # Noise columns that should not be exposed at all
    _check_noise_fields(model, findings)


def _check_schema_scope(model: SemanticModel, sel: Selection, findings: list[Finding]) -> None:
    """Flag a schema that selects nearly the whole model.

    Prep for AI is a narrowing step; selecting everything defeats it and
    degrades answer quality.
    """
    visible_tables = 0
    visible_fields = 0
    for table in model.tables:
        if table.is_hidden:
            continue
        visible_tables += 1
        visible_fields += sum(1 for c in table.columns if not c.is_hidden)
        visible_fields += sum(1 for m in table.measures if not m.is_hidden)

    if visible_tables == 0 or visible_fields == 0:
        return

    selected_fields = len(sel.columns_qualified) + len(sel.measures)
    if selected_fields == 0:
        return

    ratio = selected_fields / visible_fields
    if ratio >= 0.9:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_schema_scope",
            severity=Severity.HIGH,
            object="Copilot/schema.json",
            object_type=ObjectType.COPILOT_SCHEMA,
            message=(
                f"AI data schema selects {selected_fields} of {visible_fields} visible fields "
                f"({round(ratio * 100)}%). Prep for AI is meant to narrow the model to what the "
                "agent actually needs."
            ),
            recommendation=(
                "Deselect tables, columns, and measures outside the agent's defined scope. "
                "Fewer, well-chosen fields produce more accurate answers."
            ),
        ))


def _check_schema_dependencies(model: SemanticModel, sel: Selection, findings: list[Finding]) -> None:
    """Every measure in the schema pulls in the objects its DAX references.

    If a dependency is in the model but not in the schema, the agent can select
    the measure but cannot resolve it.
    """
    if not sel.measures:
        return

    model_measures: dict[str, tuple[str, str]] = {}
    model_columns: set[str] = set()
    for table in model.tables:
        for m in table.measures:
            model_measures[m.name] = (table.name, m.expression)
        for c in table.columns:
            model_columns.add(f"{table.name}.{c.name}".lower())

    for measure_name in sel.measures:
        entry = model_measures.get(measure_name)
        if entry is None:
            continue
        measure_table, expression = entry

        ref_columns, ref_measures = _extract_dax_refs(expression)
        missing: list[str] = []

        for dep in ref_measures:
            if dep == measure_name:
                continue
            if dep not in model_measures:
                continue  # not a measure -- likely an unqualified column
            if dep not in sel.measures:
                missing.append(f"[{dep}]")

        for dep in ref_columns:
            if dep.lower() not in model_columns:
                continue  # reference we cannot resolve
            if not sel.has_column(dep):
                missing.append(dep)

        if missing:
            unique = list(dict.fromkeys(missing))
            shown = ", ".join(unique[:4]) + (", ..." if len(unique) > 4 else "")
            findings.append(Finding(
                category=Category.AI_PREPARATION,
                check="ai_schema_dependencies",
                severity=Severity.HIGH,
                object=f"{measure_table}.{measure_name}",
                object_type=ObjectType.MEASURE,
                message=(
                    f"Measure '{measure_name}' is in the AI data schema but {len(unique)} "
                    f"object(s) it depends on are not: {shown}."
                ),
                recommendation=(
                    "Add the dependent objects to the AI data schema. Semantic Link Labs "
                    "get_measure_dependencies can enumerate these when there are many."
                ),
            ))


def _check_schema_helper_objects(model: SemanticModel, sel: Selection, findings: list[Finding]) -> None:
    """Helper and intermediate measures should not be offered to the agent."""
    for table in model.tables:
        for m in table.measures:
            if m.name not in sel.measures:
                continue
            if not HELPER_MEASURE.search(m.name):
                continue
            findings.append(Finding(
                category=Category.AI_PREPARATION,
                check="ai_schema_helper_objects",
                severity=Severity.MEDIUM,
                object=f"{table.name}.{m.name}",
                object_type=ObjectType.MEASURE,
                message=(
                    f"Measure '{m.name}' looks like a helper or intermediate calculation but is "
                    "included in the AI data schema."
                ),
                recommendation=(
                    "Remove intermediate calculations from the AI data schema. Keep only measures "
                    "a business user would ask for by name."
                ),
            ))


def _check_schema_duplicate_measures(model: SemanticModel, sel: Selection, findings: list[Finding]) -> None:
    """Two measures with the same normalized name force the agent to guess."""
    by_normalized: dict[str, list[str]] = {}
    for table in model.tables:
        for m in table.measures:
            if m.name not in sel.measures:
                continue
            key = re.sub(r"[^a-z0-9]", "", m.name.lower())
            by_normalized.setdefault(key, []).append(f"{table.name}.{m.name}")

    for refs in by_normalized.values():
        if len(refs) < 2:
            continue
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_schema_duplicate_measures",
            severity=Severity.MEDIUM,
            object=refs[0],
            object_type=ObjectType.MEASURE,
            message=(
                f"Overlapping measures are all selected in the AI data schema: {', '.join(refs)}. "
                "The agent has no basis to choose between them."
            ),
            recommendation=(
                "Keep one measure in the schema, or rename them so their difference is explicit "
                "in the name and description."
            ),
        ))


def _check_noise_fields(model: SemanticModel, findings: list[Finding]) -> None:
    for table in model.tables:
        for col in table.columns:
            if col.is_hidden:
                continue
            if not is_noise_column_name(col.name):
                continue
            findings.append(Finding(
                category=Category.AI_PREPARATION,
                check="noise_fields_excluded",
                severity=Severity.HIGH,
                object=f"{table.name}.{col.name}",
                object_type=ObjectType.COLUMN,
                message=(
                    f"Column '{col.name}' looks like a key, index, or sort helper and should not "
                    "be exposed to the agent."
                ),
                recommendation="Hide the column so it is excluded from the AI data schema.",
                auto_fixable=True,
            ))


def _check_hidden_field_conflicts(model: SemanticModel, findings: list[Finding]) -> None:
    hidden_cols: set[str] = set()
    for table in model.tables:
        for col in table.columns:
            if col.is_hidden:
                hidden_cols.add(f"{table.name}.{col.name}")
                hidden_cols.add(col.name)

    for va in model.copilot.verified_answers:
        va_id = _verified_answer_id(va)
        va_str = json.dumps(va, default=str)
        for hidden in hidden_cols:
            if hidden in va_str:
                findings.append(Finding(
                    category=Category.AI_PREPARATION,
                    check="hidden_field_conflicts",
                    severity=Severity.MEDIUM,
                    object=f"VerifiedAnswer/{va_id}",
                    object_type=ObjectType.VERIFIED_ANSWER,
                    message=(
                        f"Verified answer '{va_id}' may reference hidden column '{hidden}'. "
                        "Fields used by a verified answer must be visible or it fails silently."
                    ),
                    recommendation="Unhide the column, or rebuild the verified answer using visible fields.",
                ))
                break


# ---------------------------------------------------------------------------
# Verified Answers (Prep for AI > Verified answers)
# ---------------------------------------------------------------------------

def _check_verified_answers(model: SemanticModel, findings: list[Finding]) -> None:
    answers = model.copilot.verified_answers

    if not answers:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="verified_answers",
            severity=Severity.MEDIUM,
            object="Copilot/VerifiedAnswers/",
            object_type=ObjectType.VERIFIED_ANSWER,
            message=(
                "No verified answers found. Verified answers pin the most common business "
                "questions to a known-correct visual."
            ),
            recommendation="Collect the questions your team asks most often and create a verified answer for each.",
        ))
        return

    for va in answers:
        va_id = _verified_answer_id(va)
        triggers = _extract_triggers(va)

        # "Use 5-7 complete, robust trigger questions per verified answer"
        if len(triggers) < 5:
            findings.append(Finding(
                category=Category.AI_PREPARATION,
                check="verified_answer_quality",
                severity=Severity.LOW,
                object=f"VerifiedAnswer/{va_id}",
                object_type=ObjectType.VERIFIED_ANSWER,
                message=(
                    f"Verified answer '{va_id}' has {len(triggers)} trigger question(s). Aim for "
                    "5-7 so both exact and semantic matching have enough to work with."
                ),
                recommendation="Add trigger questions covering the different ways people ask this question.",
            ))

        # "not partial phrases" -- a trigger should be a whole question
        partials = [t for t in triggers if len(t.strip().split()) < 4]
        if partials:
            findings.append(Finding(
                category=Category.AI_PREPARATION,
                check="verified_answer_phrasing",
                severity=Severity.LOW,
                object=f"VerifiedAnswer/{va_id}",
                object_type=ObjectType.VERIFIED_ANSWER,
                message=(
                    f"Verified answer '{va_id}' has {len(partials)} very short trigger phrase(s) "
                    f"(e.g. \"{partials[0]}\"). Trigger questions should be complete questions, "
                    "not fragments."
                ),
                recommendation=(
                    "Replace fragments with full questions, and include both formal and "
                    "conversational phrasings (\"What was Q3 revenue?\" and \"how did we do last quarter\")."
                ),
            ))

        # "Configure up to 3 filters for flexible slicing"
        if _count_filters(va) == 0:
            findings.append(Finding(
                category=Category.AI_PREPARATION,
                check="verified_answer_filters",
                severity=Severity.LOW,
                object=f"VerifiedAnswer/{va_id}",
                object_type=ObjectType.VERIFIED_ANSWER,
                message=(
                    f"Verified answer '{va_id}' has no filters configured. Without them it can "
                    "only answer the one exact question."
                ),
                recommendation=(
                    "Add up to 3 filters (for example date range, region, product) so one verified "
                    "answer covers a family of questions."
                ),
            ))


# ---------------------------------------------------------------------------
# AI Instructions (Prep for AI > Add AI instructions)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _InstructionRule:
    check: str
    severity: Severity
    pattern: re.Pattern[str]
    message: str
    recommendation: str


INSTRUCTION_RULES: list[_InstructionRule] = [
    _InstructionRule(
        check="ai_instructions_terminology",
        severity=Severity.MEDIUM,
        pattern=re.compile(
            r"\b(means?|stands for|refers to|terminolog|abbreviat|acronym|glossary|defined as|we (call|define))\b",
            re.IGNORECASE,
        ),
        message=(
            "AI instructions do not define any business terminology. The agent cannot resolve "
            "org-specific terms it has never seen."
        ),
        recommendation=(
            "Define your terms explicitly, e.g. \"TMS is total media spend and should be "
            "calculated using the measure total_media_spend\"."
        ),
    ),
    _InstructionRule(
        check="ai_instructions_time_periods",
        severity=Severity.MEDIUM,
        pattern=re.compile(
            r"\b(fiscal|ytd|mtd|qtd|year to date|month to date|quarter to date|peak season|calendar year|trailing|rolling)\b",
            re.IGNORECASE,
        ),
        message=(
            "AI instructions do not define any time periods. Fiscal calendars and seasonal "
            "windows are not inferable from the model."
        ),
        recommendation=(
            "State your fiscal year boundaries and any named periods, e.g. \"our fiscal year "
            "starts July 1\"; \"peak season is November through December\"."
        ),
    ),
    _InstructionRule(
        check="ai_instructions_metric_preferences",
        severity=Severity.MEDIUM,
        pattern=re.compile(
            r"\b(use the measure|use \[|prefer|should be calculated using|default measure|when (asked|someone asks)|always use)\b",
            re.IGNORECASE,
        ),
        message=(
            "AI instructions do not state which measure to use for common questions. When several "
            "measures could answer a question, the agent guesses."
        ),
        recommendation=(
            "Name the preferred measure per question type, e.g. \"for revenue questions use "
            "[Net Revenue], not [Gross Revenue]\"."
        ),
    ),
    _InstructionRule(
        check="ai_instructions_groupings",
        severity=Severity.LOW,
        pattern=re.compile(
            r"\b(group(ed)? by|default grouping|break ?down|slice by|by default,? (show|display|group)|analysis preference)\b",
            re.IGNORECASE,
        ),
        message="AI instructions do not state default groupings or analysis preferences.",
        recommendation=(
            "Add the defaults you expect, e.g. \"when no grouping is requested, break revenue "
            "down by product category\"."
        ),
    ),
    _InstructionRule(
        check="ai_instructions_dax_examples",
        severity=Severity.LOW,
        pattern=re.compile(r"```|\bEVALUATE\b|\bSUMMARIZECOLUMNS\b|\bCALCULATE\s*\(", re.IGNORECASE),
        message=(
            "AI instructions contain no example DAX. Complex scenarios are answered more reliably "
            "when the expected query pattern is shown."
        ),
        recommendation="Add one or two example DAX queries for your hardest recurring question shapes.",
    ),
]


def _check_ai_instructions(model: SemanticModel, findings: list[Finding]) -> None:
    copilot = model.copilot

    if not copilot.instructions_exist:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_instructions_present",
            severity=Severity.HIGH,
            object=INSTRUCTIONS_OBJECT,
            object_type=ObjectType.COPILOT_INSTRUCTIONS,
            message=(
                "AI instructions file is missing. This is where business terminology, time "
                "periods, and metric preferences are taught to the agent."
            ),
            recommendation=(
                "Add Prep for AI instructions covering terminology, fiscal periods, preferred "
                "measures, and ambiguous fields."
            ),
            auto_fixable=True,
        ))
        return

    content = copilot.instructions_content
    trimmed = content.strip()

    # "Keep instructions clear and specific (don't be too verbose)"
    if len(trimmed) < 200:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_instructions_conciseness",
            severity=Severity.MEDIUM,
            object=INSTRUCTIONS_OBJECT,
            object_type=ObjectType.COPILOT_INSTRUCTIONS,
            message=(
                f"AI instructions are only {len(trimmed)} characters. That is too thin to cover "
                "terminology, time periods, and metric preferences."
            ),
            recommendation=(
                "Expand the instructions to cover your business terms, fiscal calendar, and which "
                "measure answers which question."
            ),
            auto_fixable=True,
        ))
    elif len(trimmed) > 8000:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_instructions_conciseness",
            severity=Severity.MEDIUM,
            object=INSTRUCTIONS_OBJECT,
            object_type=ObjectType.COPILOT_INSTRUCTIONS,
            message=(
                f"AI instructions are {len(trimmed)} characters. Verbose instructions slow "
                "responses and increase the chance of internal contradictions."
            ),
            recommendation=(
                "Trim to the guidance that changes the agent's behavior. Move per-field context "
                "into object descriptions instead."
            ),
        ))

    for rule in INSTRUCTION_RULES:
        if rule.pattern.search(content):
            continue
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check=rule.check,
            severity=rule.severity,
            object=INSTRUCTIONS_OBJECT,
            object_type=ObjectType.COPILOT_INSTRUCTIONS,
            message=rule.message,
            recommendation=rule.recommendation,
        ))

    _check_ambiguous_dates(model, content, findings)
    _check_advanced_object_guidance(model, content, findings)


def _check_ambiguous_dates(model: SemanticModel, content: str, findings: list[Finding]) -> None:
    """A table carrying several date columns (Order Date / Ship Date / Due Date)
    is ambiguous unless the instructions say which one to default to.
    """
    lower = content.lower()

    for table in model.tables:
        if table.is_hidden:
            continue
        date_cols = [
            c for c in table.columns
            if not c.is_hidden and (DATE_COLUMN.search(c.name) or _DATE_TYPE.search(c.data_type))
        ]
        if len(date_cols) < 2:
            continue

        mentioned = [c for c in date_cols if c.name.lower() in lower]
        if len(mentioned) >= 2:
            continue

        shown = ", ".join(c.name for c in date_cols[:3]) + (", ..." if len(date_cols) > 3 else "")
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_instructions_ambiguous_dates",
            severity=Severity.HIGH,
            object=table.name,
            object_type=ObjectType.TABLE,
            message=(
                f"Table '{table.name}' has {len(date_cols)} date columns ({shown}) but the AI "
                "instructions do not disambiguate them."
            ),
            recommendation=(
                "State the default in the instructions, e.g. \"date questions about orders use "
                "Order Date unless the user says shipped or due\"."
            ),
        ))


def _check_advanced_object_guidance(model: SemanticModel, content: str, findings: list[Finding]) -> None:
    """Calculation groups, field parameters, and DAX UDFs do not behave like
    plain measures. The checklist requires the instructions to explain them.
    """
    lower = content.lower()
    present: list[tuple[str, list[str], bool]] = []

    calc_groups = [t.name for t in model.tables if t.is_calculation_group]
    if calc_groups:
        present.append((
            "calculation group",
            calc_groups,
            "calculation group" in lower or "calculation item" in lower,
        ))

    field_params = [t.name for t in model.tables if t.is_field_parameter]
    if field_params:
        present.append(("field parameter", field_params, "field parameter" in lower))

    if model.has_udfs:
        present.append((
            "DAX user-defined function",
            [],
            "user-defined function" in lower or "user defined function" in lower or "udf" in lower,
        ))

    for label, tables, mentioned in present:
        if mentioned:
            continue
        where = f" ({', '.join(tables)})" if tables else ""
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_instructions_advanced_objects",
            severity=Severity.HIGH,
            object=tables[0] if tables else INSTRUCTIONS_OBJECT,
            object_type=ObjectType.TABLE if tables else ObjectType.COPILOT_INSTRUCTIONS,
            message=(
                f"Model uses {label}s{where} but the AI instructions never explain how to use "
                "them. The agent will not apply them correctly on its own."
            ),
            recommendation=f"Describe in the AI instructions when and how the agent should use each {label}.",
        ))


# ---------------------------------------------------------------------------
# schema.json helpers
# ---------------------------------------------------------------------------

@dataclass
class Selection:
    tables: set[str] = field(default_factory=set)
    columns_qualified: set[str] = field(default_factory=set)
    columns_bare: set[str] = field(default_factory=set)
    measures: set[str] = field(default_factory=set)

    def has_column(self, qualified: str) -> bool:
        if qualified in self.columns_qualified:
            return True
        bare = qualified[qualified.find(".") + 1:]
        return bare in self.columns_bare


def _extract_selection(schema_json: dict) -> Selection:
    """Walk Copilot/schema.json and collect the selected object names.

    The Prep for AI schema format is not contractual, so this reads it
    structurally: any array under a "tables"/"columns"/"measures" key
    contributes its entries' `name` values, at any nesting depth.
    """
    sel = Selection()
    _walk_schema(schema_json, None, "", sel)
    return sel


_CHILD_KINDS = {
    "tables": "table",
    "entities": "table",
    "columns": "column",
    "fields": "column",
    "measures": "measure",
}


def _walk_schema(node: object, kind: str | None, table_ctx: str, sel: Selection) -> None:
    if isinstance(node, list):
        for item in node:
            _walk_schema(item, kind, table_ctx, sel)
        return
    if not isinstance(node, dict):
        return

    raw_name = node.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    next_table = table_ctx

    if name:
        if kind == "table":
            sel.tables.add(name)
            next_table = name
        elif kind == "column":
            sel.columns_qualified.add(f"{table_ctx}.{name}" if table_ctx else name)
            sel.columns_bare.add(name)
        elif kind == "measure":
            sel.measures.add(name)

    for key, value in node.items():
        _walk_schema(value, _CHILD_KINDS.get(key.lower()), next_table, sel)


# ---------------------------------------------------------------------------
# Verified answer helpers (definition.json shape is not contractual)
# ---------------------------------------------------------------------------

def _verified_answer_id(va: dict) -> str:
    for key in ("name", "displayName", "id", "title"):
        v = va.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "unknown"


def _extract_triggers(va: dict) -> list[str]:
    for key in ("triggerPhrases", "trigger_phrases", "triggers", "questions", "utterances"):
        v = va.get(key)
        if isinstance(v, list):
            out = []
            for t in v:
                if isinstance(t, str):
                    out.append(t)
                elif isinstance(t, dict):
                    out.append(str(t.get("text", "")))
            return [t for t in out if t.strip()]
    return []


def _count_filters(va: dict) -> int:
    for key in ("filters", "filterConfiguration", "filter_configuration"):
        v = va.get(key)
        if isinstance(v, list):
            return len(v)
        if isinstance(v, dict):
            return len(v)
    return 0


# ---------------------------------------------------------------------------
# DAX reference extraction
# ---------------------------------------------------------------------------

QUALIFIED_COLUMN_REF = re.compile(r"'([^']+)'\[([^\]]+)\]|(?<![\w'])([A-Za-z_]\w*)\[([^\]]+)\]")
BRACKET_REF = re.compile(r"\[([^\]]+)\]")


def _extract_dax_refs(expression: str) -> tuple[list[str], list[str]]:
    """Split a DAX expression into the columns and measures it references.

    Qualified column refs are consumed first so the remaining bracket refs are
    unambiguously measure references.
    """
    columns: list[str] = []

    def _consume(m: re.Match[str]) -> str:
        table = m.group(1) or m.group(3)
        column = m.group(2) or m.group(4)
        columns.append(f"{table}.{column}")
        return " "

    stripped = QUALIFIED_COLUMN_REF.sub(_consume, expression)
    measures = [m.group(1) for m in BRACKET_REF.finditer(stripped)]

    return columns, measures


# ---------------------------------------------------------------------------
# Shared heuristics, reused by the schema-design and measure rules
# ---------------------------------------------------------------------------

def is_helper_measure_name(name: str) -> bool:
    return bool(HELPER_MEASURE.search(name))


def date_columns_of(table: TableInfo):
    """Exposed so other rule modules agree on what counts as a date column."""
    return [c for c in table.columns if DATE_COLUMN.search(c.name) or _DATE_TYPE.search(c.data_type)]
