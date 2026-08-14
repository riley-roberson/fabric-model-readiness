"""Draft the artifacts a Fabric data agent needs, from the parsed model.

Everything here is derived from what the Analyzer already read off disk, so it
works with no Fabric connection.

The organising rule, and the one the checklist marks *very important*: agent-level
instructions must not contain model-specific guidance. Agent level is for
response formatting, cross-source routing, common abbreviations, and tone. So
these generators deliberately produce a *thin* agent instruction draft and push
everything model-specific back to the model's own AI instructions, which the
Analyzer already checks.

The distinction is finer than "never name the model". Routing *by source* is the
main reason agent instructions exist -- "for revenue questions use the Sales
semantic model" is exactly right. What must not appear is the model's internals:
its tables, columns, and measures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from scout.rules.ai_prep import _extract_selection
from shared.model import SemanticModel

# Trigger phrases that read as a whole question rather than a fragment.
_QUESTION_WORDS = ("what", "how", "which", "when", "where", "who", "why", "show", "list", "compare")


@dataclass
class TableSelection:
    """The tables the agent should expose, taken from the Prep for AI schema."""

    tables: list[str] = field(default_factory=list)
    source: str = ""          # where the list came from
    complete: bool = False    # False when there is no AI data schema to read

    @property
    def count(self) -> int:
        return len(self.tables)


@dataclass
class TestQuestion:
    text: str
    origin: str      # verified_answer | measure | date_coverage
    expects: str = ""


def table_selection(model: SemanticModel) -> TableSelection:
    """The exact table list to tick in the data agent's Explorer.

    The checklist's rule is that the agent's selected tables match the Prep for
    AI schema exactly. We can read that schema, so the list is handed over
    rather than left to be re-derived by eye.
    """
    copilot = model.copilot
    if not copilot.schema_json_exists:
        return TableSelection(
            tables=[],
            source="No Copilot/schema.json -- Prep for AI has not been configured.",
            complete=False,
        )

    selection = _extract_selection(copilot.schema_json)
    tables = sorted(selection.tables)

    if not tables:
        # A schema that names columns and measures but no tables still tells us
        # which tables are in play, via the qualified column names.
        implied = {q.split(".", 1)[0] for q in selection.columns_qualified if "." in q}
        tables = sorted(implied)
        if tables:
            return TableSelection(
                tables=tables,
                source="Inferred from the columns named in Copilot/schema.json.",
                complete=True,
            )

    return TableSelection(
        tables=tables,
        source="Copilot/schema.json (Prep for AI > AI data schema)",
        complete=bool(tables),
    )


def model_object_names(model: SemanticModel) -> set[str]:
    """Every table, column, and measure name in the model.

    Used to detect model-specific text where it does not belong. Very short
    names are excluded: a two-character column would match half of any English
    sentence and make the check useless.
    """
    names: set[str] = set()
    for table in model.tables:
        if len(table.name) > 3:
            names.add(table.name)
        for col in table.columns:
            if len(col.name) > 3:
                names.add(col.name)
        for measure in table.measures:
            if len(measure.name) > 3:
                names.add(measure.name)
    return names


def find_model_specifics(text: str, model: SemanticModel) -> list[str]:
    """Model object names appearing in text that should not mention them.

    Matched on word boundaries so 'Date' does not fire on 'update'.
    """
    if not text.strip():
        return []

    found: list[str] = []
    for name in model_object_names(model):
        pattern = r"(?<![\w])" + re.escape(name) + r"(?![\w])"
        if re.search(pattern, text, re.IGNORECASE):
            found.append(name)
    return sorted(found)


def draft_agent_instructions(model: SemanticModel, *, other_sources: list[str] | None = None) -> str:
    """A scoped starting point for the agent's own instructions.

    Deliberately thin, and deliberately free of model internals. Placeholders are
    left in angle brackets so it is obvious what still needs a human.
    """
    other_sources = other_sources or []
    model_name = model.name or "the semantic model"

    lines: list[str] = [
        "## Routing",
        "",
    ]

    if other_sources:
        lines.append(
            f"Use the {model_name} semantic model for questions about "
            "<the business area this model covers>."
        )
        for source in other_sources:
            lines.append(f"Use {source} for questions about <the area {source} covers>.")
        lines.append(
            "If a question spans both, answer from the semantic model and say which "
            "source the figures came from."
        )
    else:
        lines.append(
            f"All questions are answered from the {model_name} semantic model. "
            "If a question cannot be answered from it, say so rather than guessing."
        )

    lines += [
        "",
        "## Response format",
        "",
        "State the figure first, then the period and any filters applied.",
        "Round currency to whole units unless asked otherwise.",
        "When a question is ambiguous, answer the most likely reading and say which one you took.",
        "",
        "## Abbreviations",
        "",
        "<ABBR> means <expansion>.",
        "<ABBR> means <expansion>.",
        "",
        "## Tone",
        "",
        "Answer plainly and briefly. No preamble.",
        "",
        "---",
        "",
        "Deliberately not here: which measure answers which question, how to handle",
        f"specific date columns, and what {model_name}'s tables mean. That guidance is",
        "model-specific, so it belongs in the model's own AI instructions",
        "(Prep for AI > AI instructions). Putting it at agent level is the mistake the",
        "Fabric checklist calls out as very important to avoid -- it leaks one model's",
        "internals into every source the agent can reach.",
    ]

    return "\n".join(lines)


def test_questions(model: SemanticModel, *, limit: int = 25) -> list[TestQuestion]:
    """A starting test set, so validation does not begin from a blank page.

    Drawn from three places, in descending order of confidence: verified answer
    triggers (someone already decided these matter), measures in the AI schema
    (the agent is expected to answer these), and tables with several date
    columns (the ambiguity most likely to produce a confidently wrong answer).
    """
    questions: list[TestQuestion] = []
    seen: set[str] = set()

    def add(text: str, origin: str, expects: str = "") -> None:
        key = text.strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        questions.append(TestQuestion(text=text.strip(), origin=origin, expects=expects))

    # 1. Verified answer triggers -- these must return the pinned answer.
    for va in model.copilot.verified_answers:
        name = str(va.get("name") or va.get("displayName") or va.get("id") or "verified answer")
        for key in ("triggerPhrases", "trigger_phrases", "triggers", "questions", "utterances"):
            raw = va.get(key)
            if not isinstance(raw, list):
                continue
            for item in raw:
                phrase = item if isinstance(item, str) else str(item.get("text", "")) if isinstance(item, dict) else ""
                if phrase.strip():
                    add(phrase, "verified_answer", f"the verified answer '{name}'")
            break

    # 2. Measures the agent is expected to answer with.
    selection = (
        _extract_selection(model.copilot.schema_json)
        if model.copilot.schema_json_exists
        else None
    )
    for table in model.tables:
        for measure in table.measures:
            if measure.is_hidden:
                continue
            if selection is not None and measure.name not in selection.measures:
                continue
            add(f"What is {measure.name}?", "measure", f"the {measure.name} measure")
            add(f"Show {measure.name} by year", "measure", f"{measure.name} split by year")

    # 3. Date ambiguity -- the shape most likely to be answered confidently wrong.
    from scout.rules.ai_prep import date_columns_of

    for table in model.tables:
        if table.is_hidden:
            continue
        dates = [c for c in date_columns_of(table) if not c.is_hidden]
        if len(dates) >= 2:
            add(
                f"How many {table.name} records were there last month?",
                "date_coverage",
                f"a stated choice between {', '.join(c.name for c in dates[:3])}",
            )

    return questions[:limit]
