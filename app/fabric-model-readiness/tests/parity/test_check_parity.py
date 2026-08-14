"""Holds the Python and TypeScript rule engines to the same behaviour.

The desktop app (Python, scout/rules/) and the docs site (TypeScript,
docs/src/scanner/rules/) implement the same 64 checks twice. Nothing but these
tests stops them drifting apart.

Two levels:
  - test_check_profiles_match      registration parity, pure Python, always runs
  - test_findings_match_typescript behavioural parity, needs node + esbuild
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import pytest

from scout.rules import run_all_checks
from shared.config import CHECK_PROFILES
from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    RelationshipInfo,
    SemanticModel,
    TableInfo,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
TS_RULES_INDEX = REPO_ROOT / "docs" / "src" / "scanner" / "rules" / "index.ts"
TS_RUNNER = Path(__file__).resolve().parent / "run_ts_rules.mjs"
DOCS_DIR = REPO_ROOT / "docs"


def _parse_ts_check_profiles() -> dict[str, str]:
    """Read CHECK_PROFILES out of the TypeScript source."""
    source = TS_RULES_INDEX.read_text(encoding="utf-8")
    block = re.search(r"CHECK_PROFILES[^{]*\{(.*?)\n\};", source, re.S)
    assert block, f"CHECK_PROFILES not found in {TS_RULES_INDEX}"
    return dict(re.findall(r"^\s*([a-z_0-9]+)\s*:\s*\"(ai|org|both)\"", block.group(1), re.M))


@pytest.mark.skipif(not TS_RULES_INDEX.exists(), reason="docs site not present")
def test_check_profiles_match():
    """Both engines must register the same checks under the same profiles.

    A check registered on one side only is worse than a missing check: profile
    filtering defaults unknown checks to "both", so it silently leaks into
    profiles it was never meant for.
    """
    ts_profiles = _parse_ts_check_profiles()

    assert set(CHECK_PROFILES) == set(ts_profiles), (
        f"only in Python: {sorted(set(CHECK_PROFILES) - set(ts_profiles))}\n"
        f"only in TS:     {sorted(set(ts_profiles) - set(CHECK_PROFILES))}"
    )

    mismatched = {k: (CHECK_PROFILES[k], ts_profiles[k]) for k in CHECK_PROFILES if CHECK_PROFILES[k] != ts_profiles[k]}
    assert not mismatched, f"profile tag disagreements (python, ts): {mismatched}"


def _col(name: str, **kw) -> ColumnInfo:
    return ColumnInfo(name=name, table=kw.pop("table", ""), **kw)


def _measure(name: str, expression: str, **kw) -> MeasureInfo:
    return MeasureInfo(name=name, table=kw.pop("table", ""), expression=expression, **kw)


def _exercise_model() -> SemanticModel:
    """A deliberately awful model, shaped to trip as many checks as possible.

    Kept synthetic rather than pointing at a real .SemanticModel folder so the
    test is deterministic and runs anywhere.
    """
    return SemanticModel(
        name="ParityModel",
        path="ParityModel",
        format=ModelFormat.TMDL,
        has_udfs=True,
        tables=[
            # Flat, cryptic, pivoted, housekeeping columns, wrong types
            TableInfo(
                name="CUST_TRX",
                columns=[
                    _col("CustName"),
                    _col("TR_AMT"),
                    _col("CustomerID"),
                    _col("Order Date", data_type="string"),
                    _col("Ship Date", data_type="dateTime"),
                    _col("Due Date", data_type="dateTime"),
                    _col("Total Amount", data_type="string"),
                    _col("ETL_Batch_ID"),
                    _col("CreatedBy"),
                    _col("Revenue", data_type="double", summarize_by="sum"),
                    _col("Discount Amount", data_type="double", summarize_by="sum"),
                    _col("2021"), _col("2022"), _col("2023"),
                ],
                measures=[
                    _measure("Total Revenue", "SUM('CUST_TRX'[Revenue]) + [_Base Revenue]"),
                    _measure("_Base Revenue", "SUM('CUST_TRX'[TR_AMT])"),
                ],
            ),
            # Dimension with no row label
            TableInfo(
                name="Customer",
                columns=[_col("Customer Key", is_hidden=True), _col("Customer Name"), _col("City")],
            ),
            # Calculation group the instructions never mention
            TableInfo(
                name="Time Intelligence",
                columns=[_col("Calculation Item")],
                is_calculation_group=True,
            ),
        ],
        relationships=[
            RelationshipInfo(
                from_table="Sales", from_column="Customer Key",
                to_table="Customer", to_column="Customer Key",
                is_active=True, cardinality="many:one", cross_filter_direction="oneDirection",
            ),
        ],
        copilot=CopilotConfig(
            schema_json_exists=True,
            schema_json={
                "tables": [{
                    "name": "CUST_TRX",
                    "columns": [{"name": "TR_AMT"}],
                    "measures": [{"name": "Total Revenue"}, {"name": "_Base Revenue"}],
                }],
            },
            instructions_exist=True,
            instructions_content=(
                "Answer questions about revenue using the model. Keep responses short and "
                "factual for the sales team dashboards used weekly."
            ),
            verified_answers=[
                {"name": "RevenueByRegion", "triggerPhrases": ["revenue", "show revenue by region"], "filters": []},
            ],
        ),
    )


def _signature(findings) -> Counter:
    return Counter((f.check, f.object, f.severity.value, f.object_type.value) for f in findings)


_node = shutil.which("node")


@pytest.mark.skipif(_node is None, reason="node not available")
@pytest.mark.skipif(not TS_RUNNER.exists(), reason="TS runner script missing")
@pytest.mark.skipif(not (DOCS_DIR / "node_modules" / "esbuild").exists(), reason="docs deps not installed")
def test_findings_match_typescript():
    """Same model in, same findings out -- check, object, severity, object type.

    The TS parser is bypassed: the Python-parsed model is handed to the TS rules
    directly. Parser differences are a separate concern; this pins rule logic.
    """
    model = _exercise_model()

    with tempfile.TemporaryDirectory() as tmp:
        model_path = Path(tmp) / "model.json"
        model_path.write_text(model.model_dump_json(), encoding="utf-8")

        proc = subprocess.run(
            [_node, str(TS_RUNNER), str(model_path)],
            cwd=str(DOCS_DIR),  # so node resolves esbuild from docs/node_modules
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
        )

    assert proc.returncode == 0, f"TS runner failed:\n{proc.stderr[-2000:]}"

    ts_findings = json.loads(proc.stdout)["findings"]
    ts = Counter((f["check"], f["object"], f["severity"], f["object_type"]) for f in ts_findings)
    py = _signature(run_all_checks(model))

    only_py = py - ts
    only_ts = ts - py
    assert py == ts, (
        f"python-only findings: {sorted(only_py.elements())}\n"
        f"ts-only findings:     {sorted(only_ts.elements())}"
    )

    # Guard against both engines going silently no-op.
    assert len(py) >= 20, f"expected the exercise model to trip many checks, got {len(py)}"
