"""Scout rule engine. Each module exposes a check(model) -> list[Finding] function."""

from __future__ import annotations

from shared.model import Finding, SemanticModel

from scout.rules import (
    ai_prep,
    data_consistency,
    data_types,
    measures,
    metadata,
    org_standards,
    relationships,
    schema_design,
)

ALL_RULE_MODULES = [
    schema_design,
    metadata,
    relationships,
    measures,
    ai_prep,
    data_types,
    data_consistency,
    org_standards,
]


def run_all_checks(model: SemanticModel) -> list[Finding]:
    """Run every rule module against the parsed model and collect findings."""
    findings: list[Finding] = []
    for module in ALL_RULE_MODULES:
        findings.extend(module.check(model))
    return findings
