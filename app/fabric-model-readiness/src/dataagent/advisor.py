"""What to do about this agent, in order, with where to go.

Pulls together the three sources the module has: what the model tells us, what
the agent's configuration tells us when it is known, and the checklist items that
remain a human's job.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from dataagent.checks import run_agent_checks
from dataagent.config import AgentConfig
from dataagent.generators import (
    TestQuestion,
    draft_agent_instructions,
    table_selection,
    test_questions,
)
from dataagent.locations import LOCATIONS, as_dict, location_for
from scout.rules import run_all_checks
from scout.scorer import compute_summary, estimate_totals_by_category
from shared.model import Finding, SemanticModel, Severity

CHECKLIST_FILE = Path(__file__).with_name("checklist.json")

# Below this, attaching the model to an agent produces answers nobody should act on.
READINESS_THRESHOLD = 60.0


@dataclass
class Suggestion:
    id: str
    title: str
    body: str
    severity: str            # blocker | important | advisory
    location: dict | None = None
    check: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=1)
def load_checklist() -> dict:
    return json.loads(CHECKLIST_FILE.read_text(encoding="utf-8"))


def _model_readiness(model: SemanticModel) -> tuple[float, list[Finding]]:
    findings = run_all_checks(model)
    score = compute_summary(findings, estimate_totals_by_category(findings)).score
    return score, findings


def advise(model: SemanticModel, config: AgentConfig | None = None) -> dict:
    """The full Data Agent Developer view for one model.

    Works with no agent configuration at all, in which case it reports what to
    set up rather than what is wrong.
    """
    config = config or AgentConfig()
    score, findings = _model_readiness(model)
    selection = table_selection(model)

    suggestions: list[Suggestion] = []

    # 1. Is the model fit to attach at all? An agent over an undocumented model
    #    answers confidently and wrongly, which is worse than not answering.
    blocking = [f for f in findings if f.severity == Severity.CRITICAL]
    if score < READINESS_THRESHOLD:
        # Fixing this happens in the model, not in the agent.
        suggestions.append(Suggestion(
            id="model_not_ready",
            title=f"This model scores {score} on AI readiness",
            body=(
                f"{len(blocking)} critical finding(s) remain. An agent over an undocumented model "
                "still answers -- it just answers wrongly, and confidently. Fix the criticals in the "
                "Analyzer before attaching this model to an agent."
            ),
            severity="blocker",
            location=as_dict(LOCATIONS["prep_for_ai"]),
        ))

    # 2. Prep for AI is the input to the table selection rule, so its absence
    #    blocks the one thing the checklist marks most important.
    if not selection.complete:
        suggestions.append(Suggestion(
            id="no_ai_schema",
            title="Prep for AI has not been configured",
            body=(
                "Without an AI data schema there is nothing to match the agent's table selection "
                "against, and that match is the checklist's single most important configuration rule."
            ),
            severity="blocker",
            location=as_dict(LOCATIONS["ai_data_schema"]),
        ))
    else:
        loc = location_for("agent_tables_match_ai_schema")
        suggestions.append(Suggestion(
            id="table_selection",
            title=f"Select exactly these {selection.count} table(s) in the agent",
            body=(
                "From " + selection.source + ":\n" +
                "\n".join(f"  - {t}" for t in selection.tables)
            ),
            severity="important",
            location=as_dict(loc) if loc else None,
        ))

    # 3. Anything wrong with the agent we can actually see.
    for finding in run_agent_checks(model, config):
        loc = location_for(finding["check"])
        suggestions.append(Suggestion(
            id=finding["check"],
            title=finding["message"].split(".")[0][:120],
            body=finding["message"] + (
                "\n\n" + finding["recommendation"] if finding.get("recommendation") else ""
            ),
            severity=(
                "blocker" if finding["severity"] == "critical"
                else "important" if finding["severity"] in ("high", "medium")
                else "advisory"
            ),
            location=as_dict(loc) if loc else None,
            check=finding["check"],
        ))

    # 4. Offer the drafts, once nothing structural is in the way.
    if not config.instructions.strip():
        loc = location_for("agent_instructions_present")
        suggestions.append(Suggestion(
            id="draft_instructions",
            title="Start from a scoped instruction draft",
            body=(
                "A draft is available covering routing, response format, abbreviations, and tone -- "
                "and deliberately nothing model-specific, since that belongs in the model's own "
                "AI instructions."
            ),
            severity="advisory",
            location=as_dict(loc) if loc else None,
        ))

    questions = test_questions(model)
    if questions:
        suggestions.append(Suggestion(
            id="test_set",
            title=f"{len(questions)} test questions generated",
            body=(
                "Drawn from verified answer triggers, the measures in the AI schema, and tables with "
                "more than one date column. Validation has a starting point rather than a blank page."
            ),
            severity="advisory",
        ))

    order = {"blocker": 0, "important": 1, "advisory": 2}
    suggestions.sort(key=lambda s: order.get(s.severity, 3))

    return {
        "model_name": model.name,
        "readiness_score": score,
        "readiness_threshold": READINESS_THRESHOLD,
        "critical_findings": len(blocking),
        "agent_known": config.is_known,
        "table_selection": {
            "tables": selection.tables,
            "count": selection.count,
            "source": selection.source,
            "complete": selection.complete,
        },
        "suggestions": [s.to_dict() for s in suggestions],
        "test_questions": [
            {"text": q.text, "origin": q.origin, "expects": q.expects} for q in questions
        ],
        "checklist": load_checklist(),
    }


def instructions_draft(model: SemanticModel, other_sources: list[str] | None = None) -> str:
    return draft_agent_instructions(model, other_sources=other_sources)
