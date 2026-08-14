"""Synonyms come from the culture's linguistic schema, not from the column.

Neither parser used to read the linguistic schema at all, so `synonyms` was
hardcoded empty and the check fired on every visible column of every model --
including models where the synonyms were right there on disk.
"""

from __future__ import annotations

import json

import pytest

from scout.parser import _extract_linguistic_json, _parse_tmdl_cultures

CULTURE_TEMPLATE = """\
cultureInfo en-US

\tlinguisticMetadata =
\t\t\t{json_block}
\t\tcontentType: json
"""


def _schema(entities: dict) -> str:
    payload = {"Version": "1.0.0", "Language": "en-US", "Entities": entities}
    return CULTURE_TEMPLATE.format(json_block=json.dumps(payload, indent=2))


def _write_culture(tmp_path, content: str):
    cultures = tmp_path / "cultures"
    cultures.mkdir(exist_ok=True)
    (cultures / "en-US.tmdl").write_text(content, encoding="utf-8")
    return cultures


def test_column_synonyms_are_collected(tmp_path):
    cultures = _write_culture(tmp_path, _schema({
        "customer_name": {
            "Definition": {"Binding": {"ConceptualEntity": "Customer", "ConceptualProperty": "Name"}},
            "Terms": [{"name": {}}, {"client name": {}}, {"customer name": {}}],
        },
    }))
    result = _parse_tmdl_cultures(cultures)
    assert result[("Customer", "Name")] == ["client name", "customer name"]


def test_the_column_name_itself_is_not_a_synonym(tmp_path):
    """Power BI generates a term equal to the column name; that teaches nothing."""
    cultures = _write_culture(tmp_path, _schema({
        "customer_name": {
            "Definition": {"Binding": {"ConceptualEntity": "Customer", "ConceptualProperty": "Name"}},
            "Terms": [{"name": {}}],
        },
    }))
    assert _parse_tmdl_cultures(cultures) == {}


def test_table_level_entities_are_ignored(tmp_path):
    """An entity with no ConceptualProperty binds a table, not a column."""
    cultures = _write_culture(tmp_path, _schema({
        "customer": {
            "Definition": {"Binding": {"ConceptualEntity": "Customer"}},
            "Terms": [{"client": {}}, {"buyer": {}}],
        },
    }))
    assert _parse_tmdl_cultures(cultures) == {}


def test_missing_cultures_folder_is_not_an_error(tmp_path):
    assert _parse_tmdl_cultures(tmp_path / "cultures") == {}


def test_empty_linguistic_schema_yields_nothing(tmp_path):
    """The common real-world case: Q&A was never configured."""
    cultures = _write_culture(tmp_path, CULTURE_TEMPLATE.format(
        json_block='{\n  "Version": "1.0.0",\n  "Language": "en-US"\n}'
    ))
    assert _parse_tmdl_cultures(cultures) == {}


def test_malformed_json_is_survivable(tmp_path):
    cultures = _write_culture(tmp_path, CULTURE_TEMPLATE.format(json_block='{ "Entities": '))
    assert _parse_tmdl_cultures(cultures) == {}


def test_brace_matching_survives_braces_inside_strings():
    """A regex-based extractor would stop at the brace inside the string."""
    content = 'linguisticMetadata =\n{"Version": "1.0.0", "Note": "a } brace", "Entities": {}}\ncontentType: json'
    schema = _extract_linguistic_json(content)
    assert schema is not None
    assert schema["Note"] == "a } brace"


@pytest.mark.parametrize("terms", [
    [{"revenue": {}}, {"sales": {}}],
    ["revenue", "sales"],
])
def test_term_shapes_both_supported(tmp_path, terms):
    """The schema uses objects; be tolerant of a plain-string variant too."""
    cultures = _write_culture(tmp_path, _schema({
        "fact_amount": {
            "Definition": {"Binding": {"ConceptualEntity": "Fact", "ConceptualProperty": "Amount"}},
            "Terms": terms,
        },
    }))
    assert _parse_tmdl_cultures(cultures)[("Fact", "Amount")] == ["revenue", "sales"]
