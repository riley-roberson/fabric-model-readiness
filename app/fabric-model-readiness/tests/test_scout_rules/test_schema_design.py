"""Tests for the schema design rule module."""

from shared.model import (
    ColumnInfo,
    CopilotConfig,
    ModelFormat,
    SemanticModel,
    Severity,
    TableInfo,
)
from scout.rules.schema_design import check


def _make_model(tables: list[TableInfo]) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables,
        relationships=[],
        copilot=CopilotConfig(),
    )


def test_bad_table_name():
    model = _make_model([TableInfo(name="Sheet1")])
    findings = check(model)
    naming = [f for f in findings if f.check == "table_naming"]
    assert len(naming) == 1
    assert naming[0].severity == Severity.HIGH


def test_good_table_name():
    model = _make_model([TableInfo(name="FactSales")])
    findings = check(model)
    naming = [f for f in findings if f.check == "table_naming"]
    assert len(naming) == 0


def test_wide_table():
    columns = [ColumnInfo(name=f"Col{i}", table="Wide") for i in range(35)]
    model = _make_model([TableInfo(name="Wide", columns=columns)])
    findings = check(model)
    wide = [f for f in findings if f.check == "wide_table_detection"]
    assert len(wide) == 1


def test_cross_table_duplicate_columns():
    model = _make_model([
        TableInfo(name="Customer", columns=[ColumnInfo(name="Name", table="Customer")]),
        TableInfo(name="Product", columns=[ColumnInfo(name="Name", table="Product")]),
    ])
    findings = check(model)
    dups = [f for f in findings if f.check == "cross_table_disambiguation"]
    assert len(dups) == 1
