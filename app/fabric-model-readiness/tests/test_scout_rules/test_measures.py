"""Tests for measures and calculations rule module."""

from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    SemanticModel,
    Severity,
    TableInfo,
)
from scout.rules.measures import check


def _make_model(tables: list[TableInfo]) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables,
        relationships=[],
        copilot=CopilotConfig(),
    )


# -- helper_measures_exposed -------------------------------------------------

def test_helper_measure_exposed():
    model = _make_model([TableInfo(
        name="Measures",
        measures=[MeasureInfo(name="_Helper", table="Measures", expression="1+1", is_hidden=False)],
    )])
    findings = check(model)
    exposed = [f for f in findings if f.check == "helper_measures_exposed"]
    assert len(exposed) == 1
    assert exposed[0].severity == Severity.MEDIUM


def test_helper_measure_hidden_no_finding():
    model = _make_model([TableInfo(
        name="Measures",
        measures=[MeasureInfo(name="_Helper", table="Measures", expression="1+1", is_hidden=True)],
    )])
    findings = check(model)
    exposed = [f for f in findings if f.check == "helper_measures_exposed"]
    assert len(exposed) == 0


# -- time_intelligence -------------------------------------------------------

def test_date_table_but_no_time_intelligence():
    model = _make_model([
        TableInfo(name="DimDate"),
        TableInfo(
            name="FactSales",
            measures=[MeasureInfo(name="Total", table="FactSales", expression="SUM(FactSales[Amount])")],
        ),
    ])
    findings = check(model)
    ti = [f for f in findings if f.check == "time_intelligence"]
    assert len(ti) == 1
    assert ti[0].severity == Severity.MEDIUM


def test_date_table_with_time_intelligence_no_finding():
    model = _make_model([
        TableInfo(name="Calendar"),
        TableInfo(
            name="FactSales",
            measures=[MeasureInfo(name="YTD Sales", table="FactSales", expression="TOTALYTD(SUM(FactSales[Amount]), DimDate[Date])")],
        ),
    ])
    findings = check(model)
    ti = [f for f in findings if f.check == "time_intelligence"]
    assert len(ti) == 0


# -- duplicate_measures ------------------------------------------------------

def test_duplicate_measures():
    model = _make_model([
        TableInfo(
            name="T1",
            measures=[MeasureInfo(name="Total Sales", table="T1", expression="SUM(A)")],
        ),
        TableInfo(
            name="T2",
            measures=[MeasureInfo(name="TotalSales", table="T2", expression="SUM(B)")],
        ),
    ])
    findings = check(model)
    dups = [f for f in findings if f.check == "duplicate_measures"]
    assert len(dups) == 1
    assert dups[0].severity == Severity.HIGH


# -- measure_table_required --------------------------------------------------

def test_measures_on_non_measure_table():
    model = _make_model([TableInfo(
        name="FactSales",
        columns=[ColumnInfo(name="Amount", table="FactSales")],
        measures=[MeasureInfo(name="Total", table="FactSales", expression="SUM(FactSales[Amount])")],
    )])
    findings = check(model)
    mt = [f for f in findings if f.check == "measure_table_required"]
    assert len(mt) == 1
    assert mt[0].severity == Severity.MEDIUM


def test_measures_on_measure_table_no_finding():
    model = _make_model([TableInfo(
        name="_Measures",
        measures=[MeasureInfo(name="Total", table="_Measures", expression="SUM(FactSales[Amount])")],
    )])
    findings = check(model)
    mt = [f for f in findings if f.check == "measure_table_required"]
    assert len(mt) == 0


# -- direct_measure_reference ------------------------------------------------

def test_direct_measure_reference():
    model = _make_model([TableInfo(
        name="M",
        measures=[MeasureInfo(name="Copy", table="M", expression="[Original]")],
    )])
    findings = check(model)
    direct = [f for f in findings if f.check == "direct_measure_reference"]
    assert len(direct) == 1
    assert direct[0].severity == Severity.LOW


# -- fully_qualified_columns -------------------------------------------------

def test_unqualified_column_reference():
    model = _make_model([TableInfo(
        name="M",
        measures=[MeasureInfo(name="Calc", table="M", expression="SUMX(FactSales, [Amount] * [Qty])")],
    )])
    findings = check(model)
    fq = [f for f in findings if f.check == "fully_qualified_columns"]
    assert len(fq) == 1
    assert fq[0].severity == Severity.MEDIUM


def test_qualified_column_no_finding():
    model = _make_model([TableInfo(
        name="M",
        measures=[MeasureInfo(name="Calc", table="M", expression="SUM('FactSales'[Amount])")],
    )])
    findings = check(model)
    fq = [f for f in findings if f.check == "fully_qualified_columns"]
    assert len(fq) == 0


# -- iferror_usage -----------------------------------------------------------

def test_iferror_flagged():
    model = _make_model([TableInfo(
        name="M",
        measures=[MeasureInfo(name="Safe", table="M", expression="IFERROR(1/0, 0)")],
    )])
    findings = check(model)
    ie = [f for f in findings if f.check == "iferror_usage"]
    assert len(ie) == 1
    assert ie[0].severity == Severity.LOW


# -- nested_if ---------------------------------------------------------------

def test_nested_if_flagged():
    model = _make_model([TableInfo(
        name="M",
        measures=[MeasureInfo(
            name="Category",
            table="M",
            expression="IF([Score] > 90, \"A\", IF([Score] > 70, \"B\", \"C\"))",
        )],
    )])
    findings = check(model)
    nif = [f for f in findings if f.check == "nested_if"]
    assert len(nif) == 1
    assert nif[0].severity == Severity.LOW


# -- use_divide_function -----------------------------------------------------

def test_division_operator_flagged():
    model = _make_model([TableInfo(
        name="M",
        measures=[MeasureInfo(name="Margin", table="M", expression="[Profit] / [Revenue]")],
    )])
    findings = check(model)
    div = [f for f in findings if f.check == "use_divide_function"]
    assert len(div) == 1
    assert div[0].severity == Severity.LOW


def test_divide_function_no_finding():
    model = _make_model([TableInfo(
        name="M",
        measures=[MeasureInfo(name="Margin", table="M", expression="DIVIDE([Profit], [Revenue])")],
    )])
    findings = check(model)
    div = [f for f in findings if f.check == "use_divide_function"]
    assert len(div) == 0
