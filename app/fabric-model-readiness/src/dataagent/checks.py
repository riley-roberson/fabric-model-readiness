"""Checks on the data agent itself, as opposed to the semantic model.

These sit alongside the Analyzer's 64 model checks rather than inside them: they
are about a different artifact, most of them cannot be answered from a folder on
disk, and mixing them into the model score would make it mean two things at once.

The two the Fabric checklist marks *very important* are both cross-references
between the agent and the model, and we hold the model side already:

  agent_tables_match_ai_schema        selected tables must equal the Prep for AI schema
  agent_instructions_not_model_specific   agent-level text must not name model internals
"""

from __future__ import annotations

from dataagent.config import (
    MAX_DATA_SOURCES,
    MAX_INSTRUCTION_CHARS,
    RECOMMENDED_MAX_TABLES_PER_SOURCE,
    AgentConfig,
)
from dataagent.generators import find_model_specifics, table_selection
from shared.model import Finding, SemanticModel

# check -> (severity, one-line summary)
AGENT_CHECKS: dict[str, tuple[str, str]] = {
    "agent_tables_match_ai_schema": ("critical", "Agent tables differ from the Prep for AI schema"),
    "agent_instructions_not_model_specific": ("critical", "Model-specific guidance at agent level"),
    "agent_instructions_length": ("medium", "Agent instructions too long"),
    "agent_instructions_present": ("medium", "No agent instructions"),
    "agent_datasource_count": ("high", "Too many data sources"),
    "agent_description_present": ("medium", "No description before publishing"),
    "agent_table_count": ("low", "More tables than the recommended maximum"),
    "agent_publish_drift": ("medium", "Draft and published versions differ"),
    "agent_example_queries_unavailable": ("info", "Example queries not offered for this source type"),
    "agent_lifecycle_managed": ("low", "No Git integration for the agent"),
}


class AgentFinding(Finding):
    """A Finding about the agent rather than the model.

    Reuses the Finding shape so the UI can render both alike, but these never
    enter the model's readiness score.
    """


def _finding(check: str, message: str, *, obj: str, recommendation: str = "") -> dict:
    severity, _ = AGENT_CHECKS[check]
    return {
        "check": check,
        "severity": severity,
        "object": obj,
        "message": message,
        "recommendation": recommendation,
    }


def run_agent_checks(model: SemanticModel, config: AgentConfig) -> list[dict]:
    """Everything checkable about the agent given what we know of it.

    Returns plain dicts rather than Finding objects: several of these have no
    model object to attach to, and the categories are the agent's, not the
    model's.
    """
    findings: list[dict] = []

    if not config.is_known:
        return findings

    _check_table_match(model, config, findings)
    _check_instructions(model, config, findings)
    _check_data_sources(config, findings)
    _check_publishing(config, findings)

    return findings


def _check_table_match(model: SemanticModel, config: AgentConfig, findings: list[dict]) -> None:
    """The checklist's first *very important* rule.

    Tables selected in the agent must match the Prep for AI schema. A table in
    the agent but not the schema is queryable but undocumented; a table in the
    schema but not the agent is documented but unreachable.
    """
    selection = table_selection(model)
    source = config.semantic_model_source(model.name)

    if source is None or not source.selected_tables:
        return  # nothing to compare against

    if not selection.complete:
        findings.append(_finding(
            "agent_tables_match_ai_schema",
            f"The agent exposes {len(source.selected_tables)} table(s) from this model, but the "
            "model has no Prep for AI schema to match them against.",
            obj=source.name or model.name,
            recommendation="Configure Prep for AI > AI data schema, then align the agent's table selection to it.",
        ))
        return

    expected = {t.strip().lower() for t in selection.tables}
    actual = {t.strip().lower() for t in source.selected_tables}

    only_agent = sorted(t for t in source.selected_tables if t.strip().lower() not in expected)
    only_schema = sorted(t for t in selection.tables if t.strip().lower() not in actual)

    if not only_agent and not only_schema:
        return

    parts = []
    if only_agent:
        parts.append(f"in the agent but not the AI data schema: {', '.join(only_agent[:5])}")
    if only_schema:
        parts.append(f"in the AI data schema but not the agent: {', '.join(only_schema[:5])}")

    findings.append(_finding(
        "agent_tables_match_ai_schema",
        "The agent's table selection does not match the Prep for AI schema — " + "; ".join(parts) + ".",
        obj=source.name or model.name,
        recommendation=(
            "Select exactly the tables in the AI data schema. Tables the agent can query but the "
            "schema does not describe produce unreliable answers; tables the schema describes but "
            "the agent cannot reach are simply unused."
        ),
    ))


def _check_instructions(model: SemanticModel, config: AgentConfig, findings: list[dict]) -> None:
    text = config.instructions or ""

    if not text.strip():
        findings.append(_finding(
            "agent_instructions_present",
            "The agent has no instructions. Routing, formatting, and abbreviations are left to guesswork.",
            obj=config.name or "Data agent",
            recommendation="Add agent instructions covering cross-source routing, response format, abbreviations, and tone.",
        ))
        return

    # The checklist's second *very important* rule.
    leaked = find_model_specifics(text, model)
    if leaked:
        shown = ", ".join(leaked[:6]) + (", ..." if len(leaked) > 6 else "")
        findings.append(_finding(
            "agent_instructions_not_model_specific",
            f"Agent instructions name {len(leaked)} object(s) from this semantic model ({shown}). "
            "Agent-level guidance applies to every data source, so model internals do not belong here.",
            obj=config.name or "Data agent",
            recommendation=(
                "Move this guidance into the model's own AI instructions (Prep for AI > AI instructions). "
                "Keep agent instructions to cross-source routing, response formatting, abbreviations, and tone."
            ),
        ))

    if len(text) > MAX_INSTRUCTION_CHARS:
        findings.append(_finding(
            "agent_instructions_length",
            f"Agent instructions are {len(text):,} characters, over the {MAX_INSTRUCTION_CHARS:,} character limit.",
            obj=config.name or "Data agent",
            recommendation="Trim to guidance that changes behaviour. Per-source detail belongs on the source, not the agent.",
        ))


def _check_data_sources(config: AgentConfig, findings: list[dict]) -> None:
    if len(config.data_sources) > MAX_DATA_SOURCES:
        findings.append(_finding(
            "agent_datasource_count",
            f"The agent has {len(config.data_sources)} data sources; Fabric allows {MAX_DATA_SOURCES}.",
            obj=config.name or "Data agent",
            recommendation="Remove sources the agent does not need, or split into more than one agent.",
        ))

    for source in config.data_sources:
        if len(source.selected_tables) > RECOMMENDED_MAX_TABLES_PER_SOURCE:
            findings.append(_finding(
                "agent_table_count",
                f"'{source.name}' exposes {len(source.selected_tables)} tables. Fabric recommends "
                f"{RECOMMENDED_MAX_TABLES_PER_SOURCE} or fewer per data source for best results.",
                obj=source.name,
                recommendation="Narrow the selection to the tables the agent is actually expected to answer from.",
            ))

    # Advisory, and worth saying explicitly: chasing example queries for a
    # semantic model means hunting for a control that is not there.
    for source in config.data_sources:
        if source.supports_example_queries:
            continue
        findings.append(_finding(
            "agent_example_queries_unavailable",
            f"'{source.name}' is a {source.kind.replace('_', ' ')}, and Fabric does not offer example "
            "query pairs for that source type.",
            obj=source.name,
            recommendation=(
                "Use verified answers on the semantic model instead — they serve the same purpose "
                "and the Analyzer already checks them."
            ),
        ))


def _check_publishing(config: AgentConfig, findings: list[dict]) -> None:
    if config.published and not config.description.strip():
        findings.append(_finding(
            "agent_description_present",
            "The agent is published with no description. The docs do not state that one is required, but "
            "the description is what tells colleagues what the agent is for and tells other orchestrators "
            "when to invoke it.",
            obj=config.name or "Data agent",
            recommendation="Add a description saying what the agent answers questions about, and from which data.",
        ))

    if config.has_unpublished_changes:
        findings.append(_finding(
            "agent_publish_drift",
            "The draft and published versions differ. Colleagues are querying the published version, "
            "not the one being tested.",
            obj=config.name or "Data agent",
            recommendation="Publish once the draft is validated, or note deliberately that the draft is still in progress.",
        ))

    if config.git_integration is False:
        findings.append(_finding(
            "agent_lifecycle_managed",
            "The agent's workspace has no Git integration, so instructions, example queries, and data "
            "source selections are not version-controlled.",
            obj=config.name or "Data agent",
            recommendation="Connect the workspace to Git, and use deployment pipelines to promote between environments.",
        ))
