"""TMDL doc-comment parsing.

TMDL expresses descriptions as `///` comments *above* the declaration, not as a
`description:` property. Verified against the TMDL that Microsoft's own
powerbi-modeling-mcp writer emits; it rejects `description:` outright with
"Unsupported property - description is not a supported property in the current
context".

The original parser assumed line 0 was the `table` declaration, so a documented
table -- the correct, common shape -- was silently dropped in full, taking its
columns and measures with it.
"""

from __future__ import annotations

import pytest

from scout.parser import _parse_tmdl_table

DOCUMENTED = """\
/// Customer dimension. One row per customer.
table Customer
\tlineageTag: 350e919c-01e2-4604-bd8d-0a31a90fd8b5

\t/// Surrogate key joining Customer to Fact - Sales.
\tcolumn CustomerKey
\t\tdataType: int64
\t\tisHidden
\t\tsummarizeBy: none

\tcolumn Name
\t\tdataType: string
\t\tisDefaultLabel
\t\tsummarizeBy: none

\t/// Revenue recognised in the period.
\tmeasure 'Total Revenue' = SUM('Fact - Sales'[Amount])
\t\tformatString: \\$#,0
"""

UNDOCUMENTED = """\
table Store
\tlineageTag: abc

\tcolumn StoreKey
\t\tdataType: int64
"""

# Invalid TMDL, but models hand-edited into this shape exist in the wild.
LEGACY_PROPERTY = """\
table Product
\tlineageTag: abc

\tdescription: Product dimension written the wrong way.
\tcolumn ProductKey
\t\tdataType: int64
"""


def _write(tmp_path, name: str, content: str):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_documented_table_is_not_dropped(tmp_path):
    """The regression: a /// comment above `table` used to lose the whole table."""
    table = _parse_tmdl_table(_write(tmp_path, "Customer.tmdl", DOCUMENTED))
    assert table is not None
    assert table.name == "Customer"
    assert len(table.columns) == 2
    assert len(table.measures) == 1


def test_table_description_from_doc_comment(tmp_path):
    table = _parse_tmdl_table(_write(tmp_path, "Customer.tmdl", DOCUMENTED))
    assert table.description == "Customer dimension. One row per customer."


def test_column_description_from_doc_comment(tmp_path):
    table = _parse_tmdl_table(_write(tmp_path, "Customer.tmdl", DOCUMENTED))
    col = next(c for c in table.columns if c.name == "CustomerKey")
    assert col.description == "Surrogate key joining Customer to Fact - Sales."
    assert col.is_hidden is True


def test_measure_description_from_doc_comment(tmp_path):
    table = _parse_tmdl_table(_write(tmp_path, "Customer.tmdl", DOCUMENTED))
    measure = table.measures[0]
    assert measure.name == "Total Revenue"
    assert measure.description == "Revenue recognised in the period."


def test_doc_comment_does_not_leak_to_next_object(tmp_path):
    """The Name column sits after CustomerKey and has no /// of its own."""
    table = _parse_tmdl_table(_write(tmp_path, "Customer.tmdl", DOCUMENTED))
    name_col = next(c for c in table.columns if c.name == "Name")
    assert name_col.description == ""
    assert name_col.is_default_label is True


def test_undocumented_table_still_parses(tmp_path):
    table = _parse_tmdl_table(_write(tmp_path, "Store.tmdl", UNDOCUMENTED))
    assert table is not None
    assert table.name == "Store"
    assert table.description == ""


def test_legacy_description_property_still_read(tmp_path):
    """Tolerated for models already hand-edited into the invalid shape."""
    table = _parse_tmdl_table(_write(tmp_path, "Product.tmdl", LEGACY_PROPERTY))
    assert table is not None
    assert table.description == "Product dimension written the wrong way."


@pytest.mark.parametrize("leading", ["", "\n", "\n\n"])
def test_leading_blank_lines_tolerated(tmp_path, leading):
    table = _parse_tmdl_table(_write(tmp_path, "Store.tmdl", leading + UNDOCUMENTED))
    assert table is not None
    assert table.name == "Store"
