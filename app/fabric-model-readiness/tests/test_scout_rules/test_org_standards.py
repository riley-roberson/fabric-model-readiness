"""Tests for organization-specific standards rule module."""

from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    RoleInfo,
    SemanticModel,
    Severity,
    TableInfo,
)
from scout.rules.org_standards import check


def _make_model(
    tables: list[TableInfo] | None = None,
    roles: list[RoleInfo] | None = None,
) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables or [],
        relationships=[],
        roles=roles or [],
        copilot=CopilotConfig(),
    )


# -- column_display_folders --------------------------------------------------

def test_columns_without_display_folders():
    """More than 3 visible columns without folders triggers a finding."""
    cols = [ColumnInfo(name=f"Col{i}", table="T") for i in range(5)]
    model = _make_model(tables=[TableInfo(name="T", columns=cols)])
    findings = check(model)
    folders = [f for f in findings if f.check == "column_display_folders"]
    assert len(folders) == 1
    assert folders[0].severity == Severity.MEDIUM


def test_columns_with_display_folders_no_finding():
    cols = [ColumnInfo(name=f"Col{i}", table="T", display_folder="Group") for i in range(5)]
    model = _make_model(tables=[TableInfo(name="T", columns=cols)])
    findings = check(model)
    folders = [f for f in findings if f.check == "column_display_folders"]
    assert len(folders) == 0


def test_hidden_table_skipped_for_folders():
    cols = [ColumnInfo(name=f"Col{i}", table="T") for i in range(10)]
    model = _make_model(tables=[TableInfo(name="T", columns=cols, is_hidden=True)])
    findings = check(model)
    folders = [f for f in findings if f.check == "column_display_folders"]
    assert len(folders) == 0


def test_few_columns_no_finding():
    """3 or fewer visible columns without folders is okay."""
    cols = [ColumnInfo(name=f"Col{i}", table="T") for i in range(3)]
    model = _make_model(tables=[TableInfo(name="T", columns=cols)])
    findings = check(model)
    folders = [f for f in findings if f.check == "column_display_folders"]
    assert len(folders) == 0


# -- measure_display_folders -------------------------------------------------

def test_measures_without_display_folders():
    measures = [MeasureInfo(name=f"M{i}", table="T", expression="1") for i in range(5)]
    model = _make_model(tables=[TableInfo(name="T", measures=measures)])
    findings = check(model)
    folders = [f for f in findings if f.check == "measure_display_folders"]
    assert len(folders) == 1


# -- rls_roles_defined / admin / general -------------------------------------

def test_no_rls_roles():
    model = _make_model(roles=[])
    findings = check(model)
    rls = [f for f in findings if f.check == "rls_roles_defined"]
    assert len(rls) == 1
    assert rls[0].severity == Severity.HIGH


def test_missing_admin_role():
    model = _make_model(roles=[RoleInfo(name="General")])
    findings = check(model)
    admin = [f for f in findings if f.check == "rls_admin_role"]
    assert len(admin) == 1
    assert admin[0].severity == Severity.HIGH


def test_missing_general_role():
    model = _make_model(roles=[RoleInfo(name="Admin")])
    findings = check(model)
    general = [f for f in findings if f.check == "rls_general_role"]
    assert len(general) == 1
    assert general[0].severity == Severity.HIGH


def test_both_roles_present_no_finding():
    model = _make_model(roles=[RoleInfo(name="Admin"), RoleInfo(name="General")])
    findings = check(model)
    rls = [f for f in findings if f.check in ("rls_roles_defined", "rls_admin_role", "rls_general_role")]
    assert len(rls) == 0


# -- date_table_marked -------------------------------------------------------

def test_date_table_not_marked():
    model = _make_model(tables=[TableInfo(name="DimDate", is_date_table=False)])
    findings = check(model)
    dt = [f for f in findings if f.check == "date_table_marked"]
    assert len(dt) == 1
    assert dt[0].severity == Severity.HIGH


def test_calendar_table_not_marked():
    model = _make_model(tables=[TableInfo(name="Calendar", is_date_table=False)])
    findings = check(model)
    dt = [f for f in findings if f.check == "date_table_marked"]
    assert len(dt) == 1


def test_date_table_marked_no_finding():
    model = _make_model(tables=[TableInfo(name="DimDate", is_date_table=True)])
    findings = check(model)
    dt = [f for f in findings if f.check == "date_table_marked"]
    assert len(dt) == 0


# -- userelationship_preferred -----------------------------------------------

def test_duplicate_dimension_tables():
    model = _make_model(tables=[
        TableInfo(name="DimDate"),
        TableInfo(name="DimDate_Order"),
        TableInfo(name="DimDate_Ship"),
    ])
    findings = check(model)
    ur = [f for f in findings if f.check == "userelationship_preferred"]
    assert len(ur) >= 1
    assert ur[0].severity == Severity.MEDIUM


def test_unique_dimension_tables_no_finding():
    model = _make_model(tables=[
        TableInfo(name="DimDate"),
        TableInfo(name="DimCustomer"),
    ])
    findings = check(model)
    ur = [f for f in findings if f.check == "userelationship_preferred"]
    assert len(ur) == 0
