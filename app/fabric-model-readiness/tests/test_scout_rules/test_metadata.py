"""Tests for the metadata completeness rule module."""

from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    SemanticModel,
    Severity,
    TableInfo,
)
from scout.rules.metadata import check


def _make_model(tables: list[TableInfo]) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables,
        relationships=[],
        copilot=CopilotConfig(),
    )


def test_missing_table_description():
    model = _make_model([TableInfo(name="FactSales", description="")])
    findings = check(model)
    table_desc_findings = [f for f in findings if f.check == "table_descriptions"]
    assert len(table_desc_findings) == 1
    assert table_desc_findings[0].severity == Severity.CRITICAL


def test_table_with_description_passes():
    model = _make_model([TableInfo(name="FactSales", description="Sales transactions")])
    findings = check(model)
    table_desc_findings = [f for f in findings if f.check == "table_descriptions"]
    assert len(table_desc_findings) == 0


def test_missing_measure_description():
    model = _make_model([
        TableInfo(
            name="FactSales",
            description="Sales",
            measures=[MeasureInfo(name="Total Sales", table="FactSales", expression="SUM(Amount)")],
        )
    ])
    findings = check(model)
    measure_findings = [f for f in findings if f.check == "measure_descriptions"]
    assert len(measure_findings) == 1
    assert measure_findings[0].severity == Severity.CRITICAL


def test_missing_column_description():
    model = _make_model([
        TableInfo(
            name="DimCustomer",
            description="Customers",
            columns=[ColumnInfo(name="CustomerName", table="DimCustomer")],
        )
    ])
    findings = check(model)
    col_findings = [f for f in findings if f.check == "column_descriptions"]
    assert len(col_findings) == 1


def test_hidden_column_skipped():
    model = _make_model([
        TableInfo(
            name="DimCustomer",
            description="Customers",
            columns=[ColumnInfo(name="CustomerSK", table="DimCustomer", is_hidden=True)],
        )
    ])
    findings = check(model)
    col_findings = [f for f in findings if f.check == "column_descriptions"]
    assert len(col_findings) == 0


def test_geography_data_category():
    model = _make_model([
        TableInfo(
            name="DimStore",
            description="Stores",
            columns=[
                ColumnInfo(name="City", table="DimStore", description="Store city"),
            ],
        )
    ])
    findings = check(model)
    cat_findings = [f for f in findings if f.check == "data_categories"]
    assert len(cat_findings) == 1
