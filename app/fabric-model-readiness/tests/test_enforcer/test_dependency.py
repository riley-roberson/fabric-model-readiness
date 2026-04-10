"""Tests for the dependency analysis module."""

from shared.model import (
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    SemanticModel,
    TableInfo,
    ColumnInfo,
)
from enforcer.dependency import find_dependents, safe_to_hide


def _make_model_with_measures() -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=[
            TableInfo(
                name="FactSales",
                description="Sales",
                columns=[
                    ColumnInfo(name="Amount", table="FactSales"),
                    ColumnInfo(name="SalesKey", table="FactSales"),
                ],
                measures=[
                    MeasureInfo(
                        name="Total Sales",
                        table="FactSales",
                        expression="SUM(FactSales[Amount])",
                    ),
                    MeasureInfo(
                        name="Hidden Helper",
                        table="FactSales",
                        expression="COUNTROWS(FactSales)",
                        is_hidden=True,
                    ),
                ],
            ),
        ],
        relationships=[],
        copilot=CopilotConfig(),
    )


def test_find_dependents_column():
    model = _make_model_with_measures()
    deps = find_dependents(model, "FactSales.Amount")
    assert "FactSales.Total Sales" in deps


def test_find_dependents_ignores_hidden():
    model = _make_model_with_measures()
    deps = find_dependents(model, "FactSales")
    # Hidden Helper references FactSales but is hidden, so should not appear
    assert "FactSales.Hidden Helper" not in deps


def test_safe_to_hide_blocked():
    model = _make_model_with_measures()
    is_safe, blockers = safe_to_hide(model, "FactSales.Amount")
    assert not is_safe
    assert "FactSales.Total Sales" in blockers


def test_safe_to_hide_ok():
    model = _make_model_with_measures()
    is_safe, blockers = safe_to_hide(model, "FactSales.SalesKey")
    assert is_safe
    assert blockers == []
