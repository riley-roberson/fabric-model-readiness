"""Finding-to-operation mapping.

The mapping is where a finding stops being a report and becomes a write, so the
cases that matter most are the ones it should *refuse*.
"""

from __future__ import annotations

import pytest

from enforcer.operations import CHECK_OPERATIONS, build_operations
from shared.model import (
    Category,
    ColumnInfo,
    Finding,
    ModelFormat,
    ObjectType,
    SemanticModel,
    Severity,
    TableInfo,
)


def _finding(check: str, obj: str, object_type: ObjectType, **kw) -> Finding:
    return Finding(
        category=kw.pop("category", Category.METADATA_COMPLETENESS),
        check=check,
        severity=Severity.MEDIUM,
        object=obj,
        object_type=object_type,
        message="",
        **kw,
    )


def _model(*tables: TableInfo) -> SemanticModel:
    return SemanticModel(name="M", path="M", format=ModelFormat.TMDL, tables=list(tables))


CUSTOMER = TableInfo(
    name="Customer",
    columns=[
        ColumnInfo(name="CustomerKey", table="Customer", data_type="int64"),
        ColumnInfo(name="Name", table="Customer", data_type="string"),
        ColumnInfo(name="City", table="Customer", data_type="string"),
    ],
)


def test_hidden_flag_maps_to_boolean_write():
    model = _model(CUSTOMER)
    f = _finding("surrogate_key_hidden", "Customer.CustomerKey", ObjectType.COLUMN)
    ops, unsupported = build_operations(model, [f])
    assert not unsupported
    assert len(ops) == 1
    assert ops[0].prop == "isHidden"
    assert ops[0].value is True
    assert ops[0].before is False
    assert ops[0].to_definition() == {
        "tableName": "Customer", "name": "CustomerKey", "isHidden": True,
    }


def test_table_level_write_omits_column_name():
    model = _model(CUSTOMER)
    f = _finding("fact_table_hidden", "Customer", ObjectType.TABLE, category=Category.SCHEMA_DESIGN)
    ops, _ = build_operations(model, [f])
    assert ops[0].to_definition() == {"name": "Customer", "isHidden": True}


def test_geography_category_inferred():
    model = _model(CUSTOMER)
    f = _finding("data_categories", "Customer.City", ObjectType.COLUMN)
    ops, _ = build_operations(model, [f])
    assert ops[0].value == "City"


def test_row_label_resolves_to_the_naming_column():
    """The finding is on the table; the write has to land on a column."""
    model = _model(CUSTOMER)
    f = _finding("row_label_defined", "Customer", ObjectType.TABLE)
    ops, unsupported = build_operations(model, [f])
    assert not unsupported
    assert ops[0].name == "Name"
    assert ops[0].prop == "defaultLabel"


def test_row_label_refuses_when_ambiguous():
    """Two plausible label columns is a modelling decision, not a guess."""
    table = TableInfo(
        name="Contact",
        columns=[
            ColumnInfo(name="First Name", table="Contact", data_type="string"),
            ColumnInfo(name="Last Name", table="Contact", data_type="string"),
        ],
    )
    f = _finding("row_label_defined", "Contact", ObjectType.TABLE)
    ops, unsupported = build_operations(_model(table), [f])
    assert not ops
    assert len(unsupported) == 1
    assert "row label" in unsupported[0].reason


def test_row_label_refuses_when_no_candidate():
    table = TableInfo(
        name="Date",
        columns=[ColumnInfo(name="Date", table="Date", data_type="dateTime")],
    )
    f = _finding("row_label_defined", "Date", ObjectType.TABLE)
    ops, unsupported = build_operations(_model(table), [f])
    assert not ops
    assert unsupported


def test_description_is_never_invented():
    """A placeholder description is worse than none -- the caller must supply it."""
    model = _model(CUSTOMER)
    f = _finding("column_descriptions", "Customer.Name", ObjectType.COLUMN)
    ops, unsupported = build_operations(model, [f])
    assert not ops
    assert unsupported


def test_supplied_description_is_used():
    model = _model(CUSTOMER)
    f = _finding("column_descriptions", "Customer.Name", ObjectType.COLUMN)
    ops, unsupported = build_operations(model, [f], values={f.id: "The customer's full name."})
    assert not unsupported
    assert ops[0].prop == "description"
    assert ops[0].value == "The customer's full name."


def test_structural_findings_are_reported_unsupported_not_dropped():
    """Silently ignoring these would read as 'applied' in the UI."""
    model = _model(CUSTOMER)
    f = _finding("star_schema_structure", "Customer", ObjectType.TABLE, category=Category.SCHEMA_DESIGN)
    ops, unsupported = build_operations(model, [f])
    assert not ops
    assert unsupported[0].check == "star_schema_structure"


@pytest.mark.parametrize("check", sorted(CHECK_OPERATIONS))
def test_every_mapped_check_declares_a_known_kind(check):
    kind, prop, _ = CHECK_OPERATIONS[check]
    assert kind in {"table", "column", "measure"}
    assert prop
