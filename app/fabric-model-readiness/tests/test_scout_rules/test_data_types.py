"""Tests for data types and aggregation rule module."""

from shared.model import (
    ColumnInfo,
    CopilotConfig,
    ModelFormat,
    SemanticModel,
    Severity,
    TableInfo,
)
from scout.rules.data_types import check


def _make_model(tables: list[TableInfo]) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables,
        relationships=[],
        copilot=CopilotConfig(),
    )


# -- default_summarization ---------------------------------------------------

def test_year_column_with_sum():
    model = _make_model([TableInfo(
        name="DimDate",
        columns=[ColumnInfo(name="Year", table="DimDate", data_type="Int64", summarize_by="Sum")],
    )])
    findings = check(model)
    summ = [f for f in findings if f.check == "default_summarization"]
    assert len(summ) == 1
    assert summ[0].severity == Severity.HIGH


def test_year_column_empty_summarize_numeric():
    """Empty summarize_by defaults to SUM in Power BI for numeric types."""
    model = _make_model([TableInfo(
        name="DimDate",
        columns=[ColumnInfo(name="Year", table="DimDate", data_type="Int64", summarize_by="")],
    )])
    findings = check(model)
    summ = [f for f in findings if f.check == "default_summarization"]
    assert len(summ) == 1


def test_id_column_with_sum():
    model = _make_model([TableInfo(
        name="DimCustomer",
        columns=[ColumnInfo(name="CustomerID", table="DimCustomer", data_type="Int64", summarize_by="Sum")],
    )])
    findings = check(model)
    summ = [f for f in findings if f.check == "default_summarization"]
    assert len(summ) == 1


def test_amount_column_with_sum_ok():
    """Amount is not in the NO_SUMMARIZE_KEYWORDS set, so SUM is fine."""
    model = _make_model([TableInfo(
        name="FactSales",
        columns=[ColumnInfo(name="Amount", table="FactSales", data_type="Decimal", summarize_by="Sum")],
    )])
    findings = check(model)
    summ = [f for f in findings if f.check == "default_summarization"]
    assert len(summ) == 0


def test_year_column_string_type_no_finding():
    """String types don't default to SUM, so no finding."""
    model = _make_model([TableInfo(
        name="DimDate",
        columns=[ColumnInfo(name="Year", table="DimDate", data_type="String", summarize_by="")],
    )])
    findings = check(model)
    summ = [f for f in findings if f.check == "default_summarization"]
    assert len(summ) == 0


# -- sort_by_column ----------------------------------------------------------

def test_month_name_without_sort_column():
    model = _make_model([TableInfo(
        name="DimDate",
        columns=[ColumnInfo(name="Month Name", table="DimDate", sort_by_column="")],
    )])
    findings = check(model)
    sort = [f for f in findings if f.check == "sort_by_column"]
    assert len(sort) == 1
    assert sort[0].severity == Severity.LOW


def test_month_name_with_sort_column_no_finding():
    model = _make_model([TableInfo(
        name="DimDate",
        columns=[ColumnInfo(name="Month Name", table="DimDate", sort_by_column="MonthNumber")],
    )])
    findings = check(model)
    sort = [f for f in findings if f.check == "sort_by_column"]
    assert len(sort) == 0


def test_day_label_without_sort():
    model = _make_model([TableInfo(
        name="DimDate",
        columns=[ColumnInfo(name="DayLabel", table="DimDate", sort_by_column="")],
    )])
    findings = check(model)
    sort = [f for f in findings if f.check == "sort_by_column"]
    assert len(sort) == 1


# -- avoid_float_types -------------------------------------------------------

def test_double_type_flagged():
    model = _make_model([TableInfo(
        name="FactSales",
        columns=[ColumnInfo(name="UnitPrice", table="FactSales", data_type="Double")],
    )])
    findings = check(model)
    floats = [f for f in findings if f.check == "avoid_float_types"]
    assert len(floats) == 1
    assert floats[0].severity == Severity.MEDIUM


def test_decimal_type_ok():
    model = _make_model([TableInfo(
        name="FactSales",
        columns=[ColumnInfo(name="UnitPrice", table="FactSales", data_type="Decimal")],
    )])
    findings = check(model)
    floats = [f for f in findings if f.check == "avoid_float_types"]
    assert len(floats) == 0
