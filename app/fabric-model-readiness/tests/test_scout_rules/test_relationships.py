"""Tests for relationship rule module."""

from shared.model import (
    CopilotConfig,
    ModelFormat,
    RelationshipInfo,
    SemanticModel,
    Severity,
    TableInfo,
)
from scout.rules.relationships import check


def _make_model(
    tables: list[TableInfo] | None = None,
    relationships: list[RelationshipInfo] | None = None,
) -> SemanticModel:
    return SemanticModel(
        name="TestModel",
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables or [],
        relationships=relationships or [],
        copilot=CopilotConfig(),
    )


# -- missing_relationships (orphaned tables) ---------------------------------

def test_orphaned_table():
    model = _make_model(
        tables=[TableInfo(name="Orphan", is_hidden=False)],
        relationships=[],
    )
    findings = check(model)
    orphan = [f for f in findings if f.check == "missing_relationships"]
    assert len(orphan) == 1
    assert orphan[0].severity == Severity.CRITICAL


def test_hidden_table_not_flagged_as_orphan():
    model = _make_model(
        tables=[TableInfo(name="HiddenTable", is_hidden=True)],
        relationships=[],
    )
    findings = check(model)
    orphan = [f for f in findings if f.check == "missing_relationships"]
    assert len(orphan) == 0


def test_connected_table_not_flagged():
    model = _make_model(
        tables=[
            TableInfo(name="FactSales"),
            TableInfo(name="DimProduct"),
        ],
        relationships=[RelationshipInfo(
            from_table="FactSales", from_column="ProductKey",
            to_table="DimProduct", to_column="ProductKey",
        )],
    )
    findings = check(model)
    orphan = [f for f in findings if f.check == "missing_relationships"]
    assert len(orphan) == 0


# -- inactive_relationships --------------------------------------------------

def test_inactive_relationship():
    model = _make_model(
        tables=[TableInfo(name="A"), TableInfo(name="B")],
        relationships=[RelationshipInfo(
            from_table="A", from_column="Key",
            to_table="B", to_column="Key",
            is_active=False,
        )],
    )
    findings = check(model)
    inactive = [f for f in findings if f.check == "inactive_relationships"]
    assert len(inactive) == 1
    assert inactive[0].severity == Severity.MEDIUM


def test_active_relationship_no_finding():
    model = _make_model(
        tables=[TableInfo(name="A"), TableInfo(name="B")],
        relationships=[RelationshipInfo(
            from_table="A", from_column="Key",
            to_table="B", to_column="Key",
            is_active=True,
        )],
    )
    findings = check(model)
    inactive = [f for f in findings if f.check == "inactive_relationships"]
    assert len(inactive) == 0


# -- cardinality_correctness (many-to-many) ----------------------------------

def test_many_to_many_relationship():
    model = _make_model(
        relationships=[RelationshipInfo(
            from_table="A", from_column="Key",
            to_table="B", to_column="Key",
            cardinality="ManyToMany",
        )],
    )
    findings = check(model)
    m2m = [f for f in findings if f.check == "cardinality_correctness"]
    assert len(m2m) == 1
    assert m2m[0].severity == Severity.HIGH


def test_one_to_many_no_finding():
    model = _make_model(
        relationships=[RelationshipInfo(
            from_table="A", from_column="Key",
            to_table="B", to_column="Key",
            cardinality="OneToMany",
        )],
    )
    findings = check(model)
    m2m = [f for f in findings if f.check == "cardinality_correctness"]
    assert len(m2m) == 0


# -- bidirectional_relationship ----------------------------------------------

def test_bidirectional_relationship():
    model = _make_model(
        relationships=[RelationshipInfo(
            from_table="A", from_column="Key",
            to_table="B", to_column="Key",
            cross_filter_direction="BothDirections",
        )],
    )
    findings = check(model)
    bidir = [f for f in findings if f.check == "bidirectional_relationship"]
    assert len(bidir) == 1
    assert bidir[0].severity == Severity.HIGH


def test_single_direction_no_finding():
    model = _make_model(
        relationships=[RelationshipInfo(
            from_table="A", from_column="Key",
            to_table="B", to_column="Key",
            cross_filter_direction="SingleDirection",
        )],
    )
    findings = check(model)
    bidir = [f for f in findings if f.check == "bidirectional_relationship"]
    assert len(bidir) == 0


# -- ambiguous_paths ---------------------------------------------------------

def test_ambiguous_paths_duplicate_edge():
    """Two active relationships from same source to same target."""
    model = _make_model(
        relationships=[
            RelationshipInfo(
                from_table="Fact", from_column="Key1",
                to_table="Dim", to_column="Key1",
                is_active=True,
            ),
            RelationshipInfo(
                from_table="Fact", from_column="Key2",
                to_table="Dim", to_column="Key2",
                is_active=True,
            ),
        ],
    )
    findings = check(model)
    ambig = [f for f in findings if f.check == "ambiguous_paths"]
    assert len(ambig) >= 1
