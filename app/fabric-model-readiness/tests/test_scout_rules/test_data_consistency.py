"""Tests for data consistency rule module."""

from shared.model import (
    CopilotConfig,
    ModelFormat,
    SemanticModel,
    TableInfo,
)
from scout.rules.data_consistency import check


def _make_model(tables: list[TableInfo]) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables,
        relationships=[],
        copilot=CopilotConfig(),
    )


def test_partitioned_tables_detected():
    model = _make_model([
        TableInfo(name="Sales2020"),
        TableInfo(name="Sales2021"),
        TableInfo(name="Sales2022"),
    ])
    findings = check(model)
    partitioned = [f for f in findings if f.check == "partitioned_tables"]
    assert len(partitioned) == 1
    assert "Sales2020" in partitioned[0].message


def test_single_year_table_no_finding():
    model = _make_model([TableInfo(name="Sales2023")])
    findings = check(model)
    partitioned = [f for f in findings if f.check == "partitioned_tables"]
    assert len(partitioned) == 0


def test_no_year_suffix_no_finding():
    model = _make_model([
        TableInfo(name="FactSales"),
        TableInfo(name="DimCustomer"),
    ])
    findings = check(model)
    partitioned = [f for f in findings if f.check == "partitioned_tables"]
    assert len(partitioned) == 0
