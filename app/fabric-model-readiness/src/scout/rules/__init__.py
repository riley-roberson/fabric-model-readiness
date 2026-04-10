"""Scout rule engine. Each module exposes a check(model) -> list[Finding] function."""

from __future__ import annotations

from shared.config import CHECK_PROFILES
from shared.model import Finding, Profile, SemanticModel

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


def filter_by_profile(findings: list[Finding], profile: Profile) -> list[Finding]:
    """Keep only findings whose check belongs to the active profile.

    - BOTH: returns all findings unchanged.
    - AI: keeps checks tagged "ai" or "both".
    - ORG: keeps checks tagged "org" or "both".

    Unknown checks (not in CHECK_PROFILES) default to "both" so they are
    always included.
    """
    if profile == Profile.BOTH:
        return findings

    if profile == Profile.AI:
        allowed = {"ai", "both"}
    else:
        allowed = {"org", "both"}

    return [f for f in findings if CHECK_PROFILES.get(f.check, "both") in allowed]
