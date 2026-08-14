"""Phase-aware linting: when each check starts being worth reporting.

Scout emits all 64 checks whatever state a project is in. On a half-built model
that is not a report, it is noise, and it produces a score against a bar the
project was never meant to clear yet.

Each check is mapped to the earliest stage at which it is *meaningful*. Before
that stage it is suppressed entirely rather than greyed out, because a finding
you cannot act on yet is worse than no finding.

One correction to the obvious intuition: Scout parses the .SemanticModel folder,
so it cannot see the warehouse at all. Nothing it checks is observable during
bronze, silver, or gold -- the model does not exist yet. Warehouse-layer naming
becomes checkable only once the model imports those tables and their source
names appear in the partition expressions. So the earliest meaningful stage for
every current check is pbi_development or later.
"""

from __future__ import annotations

from shared.config import CHECK_PROFILES

from sidekick.process import load_process

# Stage at which a check first becomes meaningful.
CHECK_STAGES: dict[str, str] = {
    # -- Semantic Model Development in Power BI ------------------------------
    # Everything structural, and every org standard, becomes observable as soon
    # as the model exists.
    "table_naming": "pbi_development",
    "column_naming": "pbi_development",
    "measure_naming": "pbi_development",
    "wide_table_detection": "pbi_development",
    "fact_table_hidden": "pbi_development",
    "surrogate_key_hidden": "pbi_development",
    "cross_table_disambiguation": "pbi_development",
    "star_schema_structure": "pbi_development",
    "business_friendly_names": "pbi_development",
    "unnecessary_columns": "pbi_development",
    "missing_relationships": "pbi_development",
    "inactive_relationships": "pbi_development",
    "cardinality_correctness": "pbi_development",
    "bidirectional_relationship": "pbi_development",
    "ambiguous_paths": "pbi_development",
    "helper_measures_exposed": "pbi_development",
    "time_intelligence": "pbi_development",
    "explicit_measures": "pbi_development",
    "duplicate_measures": "pbi_development",
    "measure_table_required": "pbi_development",
    "direct_measure_reference": "pbi_development",
    "fully_qualified_columns": "pbi_development",
    "shortened_calculate": "pbi_development",
    "iferror_usage": "pbi_development",
    "nested_if": "pbi_development",
    "use_divide_function": "pbi_development",
    "default_summarization": "pbi_development",
    "sort_by_column": "pbi_development",
    "incorrect_data_types": "pbi_development",
    "avoid_float_types": "pbi_development",
    "partitioned_tables": "pbi_development",
    "column_display_folders": "pbi_development",
    "measure_display_folders": "pbi_development",
    "date_table_marked": "pbi_development",
    "userelationship_preferred": "pbi_development",
    "rls_roles_defined": "pbi_development",
    "rls_admin_role": "pbi_development",
    "rls_general_role": "pbi_development",
    "data_categories": "pbi_development",

    # -- AI Readiness --------------------------------------------------------
    # Documentation and Data Agent configuration. Descriptions sit here rather
    # than with model development because their purpose is to teach an agent,
    # and demanding them mid-build buries everything else.
    "table_descriptions": "ai_readiness",
    "column_descriptions": "ai_readiness",
    "measure_descriptions": "ai_readiness",
    "synonyms": "ai_readiness",
    "row_label_defined": "ai_readiness",
    "ai_schema_configured": "ai_readiness",
    "ai_schema_scope": "ai_readiness",
    "ai_schema_dependencies": "ai_readiness",
    "ai_schema_helper_objects": "ai_readiness",
    "ai_schema_duplicate_measures": "ai_readiness",
    "noise_fields_excluded": "ai_readiness",
    "hidden_field_conflicts": "ai_readiness",
    "verified_answers": "ai_readiness",
    "verified_answer_quality": "ai_readiness",
    "verified_answer_phrasing": "ai_readiness",
    "verified_answer_filters": "ai_readiness",
    "ai_instructions_present": "ai_readiness",
    "ai_instructions_conciseness": "ai_readiness",
    "ai_instructions_terminology": "ai_readiness",
    "ai_instructions_time_periods": "ai_readiness",
    "ai_instructions_metric_preferences": "ai_readiness",
    "ai_instructions_ambiguous_dates": "ai_readiness",
    "ai_instructions_groupings": "ai_readiness",
    "ai_instructions_dax_examples": "ai_readiness",
    "ai_instructions_advanced_objects": "ai_readiness",
}

# Checks not yet mapped fall here. Deliberately the stage where a model first
# exists: a new check should surface too early rather than never.
DEFAULT_STAGE = "pbi_development"


def stage_of(check: str) -> str:
    return CHECK_STAGES.get(check, DEFAULT_STAGE)


def active_checks(stage_id: str) -> set[str]:
    """Checks meaningful at this stage or any earlier one."""
    process = load_process()
    reached = {s.id for s in process.stages_up_to(stage_id)}
    return {check for check in CHECK_PROFILES if stage_of(check) in reached}


def filter_by_stage(findings: list, stage_id: str) -> list:
    """Drop findings whose check is not yet meaningful."""
    allowed = active_checks(stage_id)
    return [f for f in findings if f.check in allowed]


def stage_progress(findings: list, stage_id: str) -> dict:
    """How the project is doing against what should be true *now*.

    Returns the stage-scoped finding counts alongside the number of checks in
    play, so the UI can say "82% of what should be true at this stage" instead
    of scoring against a bar the project has not reached.
    """
    allowed = active_checks(stage_id)
    scoped = [f for f in findings if f.check in allowed]
    failing = {f.check for f in scoped}

    total = len(allowed)
    passing = total - len(failing)
    percent = round(100 * passing / total) if total else 100

    return {
        "stage": stage_id,
        "checks_in_play": total,
        "checks_passing": passing,
        "checks_failing": len(failing),
        "percent": percent,
        "findings": len(scoped),
        "suppressed": len(findings) - len(scoped),
    }
