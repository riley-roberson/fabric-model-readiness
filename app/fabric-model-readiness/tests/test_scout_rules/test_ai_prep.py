"""Tests for AI preparation rule module."""

import pytest

from scout.rules import ai_prep
from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    SemanticModel,
    Severity,
    TableInfo,
)
from scout.rules.ai_prep import check


def _make_model(
    tables: list[TableInfo] | None = None,
    copilot: CopilotConfig | None = None,
) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables or [],
        relationships=[],
        copilot=copilot or CopilotConfig(),
    )


# -- ai_schema_configured ---------------------------------------------------

def test_missing_ai_schema():
    model = _make_model(copilot=CopilotConfig(schema_json_exists=False))
    findings = check(model)
    schema = [f for f in findings if f.check == "ai_schema_configured"]
    assert len(schema) == 1
    assert schema[0].severity == Severity.CRITICAL


def test_ai_schema_present_no_finding():
    model = _make_model(copilot=CopilotConfig(schema_json_exists=True, schema_json={"tables": []}))
    findings = check(model)
    schema = [f for f in findings if f.check == "ai_schema_configured"]
    assert len(schema) == 0


# -- ai_instructions_present / quality --------------------------------------

def test_missing_ai_instructions():
    model = _make_model(copilot=CopilotConfig(instructions_exist=False))
    findings = check(model)
    instr = [f for f in findings if f.check == "ai_instructions_present"]
    assert len(instr) == 1
    assert instr[0].severity == Severity.HIGH


def test_short_ai_instructions():
    model = _make_model(copilot=CopilotConfig(instructions_exist=True, instructions_content="Short."))
    findings = check(model)
    quality = [f for f in findings if f.check == "ai_instructions_conciseness"]
    assert len(quality) == 1
    assert quality[0].severity == Severity.MEDIUM


def test_verbose_ai_instructions():
    model = _make_model(copilot=CopilotConfig(instructions_exist=True, instructions_content="x" * 8001))
    findings = check(model)
    quality = [f for f in findings if f.check == "ai_instructions_conciseness"]
    assert len(quality) == 1


def test_good_ai_instructions_no_finding():
    long_content = "This model covers sales and inventory data for the retail division. " * 5
    model = _make_model(copilot=CopilotConfig(instructions_exist=True, instructions_content=long_content))
    findings = check(model)
    quality = [f for f in findings if f.check in ("ai_instructions_present", "ai_instructions_conciseness")]
    assert len(quality) == 0


# -- verified_answers --------------------------------------------------------

def test_no_verified_answers():
    model = _make_model(copilot=CopilotConfig(verified_answers=[]))
    findings = check(model)
    va = [f for f in findings if f.check == "verified_answers"]
    assert len(va) == 1
    assert va[0].severity == Severity.MEDIUM


def test_verified_answer_few_triggers():
    model = _make_model(copilot=CopilotConfig(verified_answers=[
        {"id": "va1", "triggerPhrases": ["sales", "revenue"]},
    ]))
    findings = check(model)
    quality = [f for f in findings if f.check == "verified_answer_quality"]
    assert len(quality) == 1
    assert quality[0].severity == Severity.LOW


def test_verified_answer_enough_triggers_no_finding():
    model = _make_model(copilot=CopilotConfig(verified_answers=[
        {"id": "va1", "triggerPhrases": ["a", "b", "c", "d", "e"]},
    ]))
    findings = check(model)
    quality = [f for f in findings if f.check == "verified_answer_quality"]
    assert len(quality) == 0


# -- noise_fields_excluded ---------------------------------------------------

def test_noise_field_id_column_not_hidden():
    model = _make_model(
        tables=[TableInfo(
            name="DimCustomer",
            columns=[ColumnInfo(name="CustomerID", table="DimCustomer", is_hidden=False)],
        )],
        copilot=CopilotConfig(schema_json_exists=True, schema_json={}),
    )
    findings = check(model)
    noise = [f for f in findings if f.check == "noise_fields_excluded"]
    assert len(noise) == 1
    assert noise[0].severity == Severity.HIGH


def test_noise_field_hidden_no_finding():
    model = _make_model(
        tables=[TableInfo(
            name="DimCustomer",
            columns=[ColumnInfo(name="CustomerID", table="DimCustomer", is_hidden=True)],
        )],
        copilot=CopilotConfig(schema_json_exists=True, schema_json={}),
    )
    findings = check(model)
    noise = [f for f in findings if f.check == "noise_fields_excluded"]
    assert len(noise) == 0


def test_noise_field_sort_key():
    model = _make_model(
        tables=[TableInfo(
            name="DimDate",
            columns=[ColumnInfo(name="MonthSort", table="DimDate", is_hidden=False)],
        )],
        copilot=CopilotConfig(schema_json_exists=True, schema_json={}),
    )
    findings = check(model)
    noise = [f for f in findings if f.check == "noise_fields_excluded"]
    assert len(noise) == 1


@pytest.mark.parametrize("name", [
    "CustomerID", "Customer ID", "Customer_ID", "CustomerKey", "SalesKey",
    "MonthSort", "SortOrder", "sort_order", "SK_Customer", "RowVersion", "GUID",
])
def test_noise_names_flagged(name):
    """camelCase forms are the common case and were previously missed."""
    assert ai_prep.is_noise_column_name(name), f"{name} should be noise"


@pytest.mark.parametrize("name", [
    "Valid", "Paid", "Monkey", "Category", "Revenue", "Customer Name",
    "Purchase Order", "Whiskey", "Turnkey",
])
def test_business_names_not_flagged(name):
    """The token boundary is what keeps these from matching on a substring."""
    assert not ai_prep.is_noise_column_name(name), f"{name} should not be noise"


# -- hidden_field_conflicts --------------------------------------------------

def test_hidden_field_conflict_without_ai_schema():
    """A verified answer on a hidden column fails regardless of schema.json.

    Regression: this check used to sit behind the schema_json_exists early
    return, so it never ran on the models most likely to have the problem.
    """
    model = _make_model(
        tables=[TableInfo(
            name="FactSales",
            columns=[ColumnInfo(name="SalesKey", table="FactSales", is_hidden=True)],
        )],
        copilot=CopilotConfig(
            schema_json_exists=False,
            verified_answers=[{"id": "va1", "definition": "uses FactSales.SalesKey for filtering"}],
        ),
    )
    findings = check(model)
    assert len([f for f in findings if f.check == "hidden_field_conflicts"]) == 1


def test_hidden_field_in_verified_answer():
    model = _make_model(
        tables=[TableInfo(
            name="FactSales",
            columns=[ColumnInfo(name="SalesKey", table="FactSales", is_hidden=True)],
        )],
        copilot=CopilotConfig(verified_answers=[
            {"id": "va1", "definition": "uses FactSales.SalesKey for filtering"},
        ]),
    )
    findings = check(model)
    conflicts = [f for f in findings if f.check == "hidden_field_conflicts"]
    assert len(conflicts) == 1
    assert conflicts[0].severity == Severity.MEDIUM


def test_no_hidden_field_conflict():
    model = _make_model(
        tables=[TableInfo(
            name="FactSales",
            columns=[ColumnInfo(name="Amount", table="FactSales", is_hidden=False)],
        )],
        copilot=CopilotConfig(verified_answers=[
            {"id": "va1", "definition": "uses FactSales.Amount"},
        ]),
    )
    findings = check(model)
    conflicts = [f for f in findings if f.check == "hidden_field_conflicts"]
    assert len(conflicts) == 0
