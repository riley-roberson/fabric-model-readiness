"""Agent-side checks, especially the two the checklist marks *very important*."""

from __future__ import annotations

import pytest

from dataagent.checks import AGENT_CHECKS, run_agent_checks
from dataagent.config import AgentConfig, AgentDataSource
from dataagent.generators import find_model_specifics
from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    SemanticModel,
    TableInfo,
)


def _model(schema: dict | None = None) -> SemanticModel:
    return SemanticModel(
        name="Sales",
        path="Sales",
        format=ModelFormat.TMDL,
        tables=[
            TableInfo(
                name="Customer",
                columns=[ColumnInfo(name="Customer Name", table="Customer", data_type="string")],
            ),
            TableInfo(
                name="Fact Sales",
                columns=[ColumnInfo(name="Amount", table="Fact Sales", data_type="double")],
                measures=[MeasureInfo(name="Total Revenue", table="Fact Sales", expression="SUM(x)")],
            ),
        ],
        copilot=CopilotConfig(
            schema_json_exists=schema is not None,
            schema_json=schema or {},
        ),
    )


AI_SCHEMA = {"tables": [{"name": "Customer"}, {"name": "Fact Sales"}]}


def _checks(findings) -> set[str]:
    return {f["check"] for f in findings}


# -- rule 1: agent tables must equal the AI data schema ----------------------

def test_matching_tables_produce_no_finding():
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name="Sales", selected_tables=["Customer", "Fact Sales"])],
    )
    assert "agent_tables_match_ai_schema" not in _checks(run_agent_checks(_model(AI_SCHEMA), config))


def test_extra_table_in_agent_is_flagged():
    """Queryable but undocumented -- the agent will answer from it regardless."""
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name="Sales", selected_tables=["Customer", "Fact Sales", "Staging"])],
    )
    findings = run_agent_checks(_model(AI_SCHEMA), config)
    hit = next(f for f in findings if f["check"] == "agent_tables_match_ai_schema")
    assert "Staging" in hit["message"]
    assert hit["severity"] == "critical"


def test_missing_table_in_agent_is_flagged():
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name="Sales", selected_tables=["Customer"])],
    )
    hit = next(
        f for f in run_agent_checks(_model(AI_SCHEMA), config)
        if f["check"] == "agent_tables_match_ai_schema"
    )
    assert "Fact Sales" in hit["message"]


def test_table_comparison_ignores_case_and_padding():
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name="Sales", selected_tables=[" customer ", "FACT SALES"])],
    )
    assert "agent_tables_match_ai_schema" not in _checks(run_agent_checks(_model(AI_SCHEMA), config))


def test_no_ai_schema_is_reported_rather_than_compared():
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name="Sales", selected_tables=["Customer"])],
    )
    hit = next(
        f for f in run_agent_checks(_model(None), config)
        if f["check"] == "agent_tables_match_ai_schema"
    )
    assert "no Prep for AI schema" in hit["message"]


# -- rule 2: no model-specific guidance at agent level ------------------------

def test_model_object_in_agent_instructions_is_flagged():
    config = AgentConfig(
        name="A",
        instructions="For revenue questions use the Total Revenue measure.",
    )
    hit = next(
        f for f in run_agent_checks(_model(AI_SCHEMA), config)
        if f["check"] == "agent_instructions_not_model_specific"
    )
    assert "Total Revenue" in hit["message"]
    assert hit["severity"] == "critical"


def test_cross_source_routing_is_not_flagged():
    """Naming the model for routing is the whole point of agent instructions.

    What is forbidden is the model's *internals*, not its name.
    """
    config = AgentConfig(
        name="A",
        instructions=(
            "For revenue questions use the Sales semantic model. "
            "For delivery performance use the Ops KQL database. "
            "TMS means total media spend. Answer plainly."
        ),
    )
    assert "agent_instructions_not_model_specific" not in _checks(
        run_agent_checks(_model(AI_SCHEMA), config)
    )


def test_short_names_do_not_trigger_false_positives():
    """A three-letter column would otherwise match half of any sentence."""
    model = SemanticModel(
        name="M", path="M", format=ModelFormat.TMDL,
        tables=[TableInfo(name="T", columns=[ColumnInfo(name="Qty", table="T")])],
    )
    assert find_model_specifics("Answer using the qty of words you need.", model) == []


def test_object_names_match_on_word_boundaries():
    """'Date' must not fire on 'update'."""
    model = SemanticModel(
        name="M", path="M", format=ModelFormat.TMDL,
        tables=[TableInfo(name="Date", columns=[])],
    )
    assert find_model_specifics("Please update the figures.", model) == []
    assert find_model_specifics("Use the Date table.", model) == ["Date"]


# -- the rest -----------------------------------------------------------------

def test_semantic_models_are_told_example_queries_do_not_exist():
    """Fabric offers no example query pairs for semantic models or ontologies."""
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name="Sales", kind="semantic_model")],
    )
    hit = next(
        f for f in run_agent_checks(_model(AI_SCHEMA), config)
        if f["check"] == "agent_example_queries_unavailable"
    )
    assert "verified answers" in hit["recommendation"]


def test_lakehouse_sources_are_not_told_that():
    config = AgentConfig(name="A", data_sources=[AgentDataSource(name="Ops", kind="lakehouse")])
    assert "agent_example_queries_unavailable" not in _checks(run_agent_checks(_model(AI_SCHEMA), config))


def test_more_than_five_data_sources_is_flagged():
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name=f"S{i}", kind="lakehouse") for i in range(6)],
    )
    assert "agent_datasource_count" in _checks(run_agent_checks(_model(AI_SCHEMA), config))


def test_table_count_advisory_at_the_recommended_maximum():
    config = AgentConfig(
        name="A",
        data_sources=[AgentDataSource(name="Sales", selected_tables=[f"T{i}" for i in range(26)])],
    )
    assert "agent_table_count" in _checks(run_agent_checks(_model(None), config))


def test_instructions_over_the_character_cap():
    config = AgentConfig(name="A", instructions="x" * 15_001)
    assert "agent_instructions_length" in _checks(run_agent_checks(_model(AI_SCHEMA), config))


def test_unknown_configuration_yields_nothing():
    """Absence of information is not evidence of a problem."""
    assert run_agent_checks(_model(AI_SCHEMA), AgentConfig()) == []


@pytest.mark.parametrize("check", sorted(AGENT_CHECKS))
def test_every_check_declares_a_known_severity(check):
    severity, summary = AGENT_CHECKS[check]
    assert severity in {"critical", "high", "medium", "low", "info"}
    assert summary
