"""AI preparation checks: schema.json, instructions, verified answers, noise fields."""

from __future__ import annotations

from shared.model import Category, Finding, ObjectType, SemanticModel, Severity


def check(model: SemanticModel) -> list[Finding]:
    findings: list[Finding] = []
    copilot = model.copilot

    # AI schema exists
    if not copilot.schema_json_exists:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_schema_configured",
            severity=Severity.CRITICAL,
            object="Copilot/schema.json",
            object_type=ObjectType.COPILOT_SCHEMA,
            message="AI schema (Copilot/schema.json) is missing entirely. Copilot needs this to know which fields to use.",
            auto_fixable=False,
        ))

    # AI instructions exist
    if not copilot.instructions_exist:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_instructions_present",
            severity=Severity.HIGH,
            object="Copilot/Instructions/instructions.md",
            object_type=ObjectType.COPILOT_INSTRUCTIONS,
            message="AI instructions file is missing. Add business context, terminology, and metric preferences.",
            auto_fixable=True,
        ))
    elif len(copilot.instructions_content.strip()) < 50:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="ai_instructions_quality",
            severity=Severity.MEDIUM,
            object="Copilot/Instructions/instructions.md",
            object_type=ObjectType.COPILOT_INSTRUCTIONS,
            message="AI instructions exist but are very short. Add business terms, time periods, metric preferences, and default groupings.",
            auto_fixable=True,
        ))

    # Verified answers
    if not copilot.verified_answers:
        findings.append(Finding(
            category=Category.AI_PREPARATION,
            check="verified_answers",
            severity=Severity.MEDIUM,
            object="Copilot/VerifiedAnswers/",
            object_type=ObjectType.VERIFIED_ANSWER,
            message="No verified answers found. Add at least a few verified answers for common business questions.",
            auto_fixable=False,
        ))
    else:
        for va in copilot.verified_answers:
            triggers = va.get("triggerPhrases", va.get("trigger_phrases", []))
            va_id = va.get("id", "unknown")
            if len(triggers) < 5:
                findings.append(Finding(
                    category=Category.AI_PREPARATION,
                    check="verified_answer_quality",
                    severity=Severity.LOW,
                    object=f"VerifiedAnswer/{va_id}",
                    object_type=ObjectType.VERIFIED_ANSWER,
                    message=f"Verified answer '{va_id}' has only {len(triggers)} trigger phrases. Aim for 5-7 covering formal and conversational variations.",
                    auto_fixable=False,
                ))

    # Noise fields in AI schema (ID columns, sort helpers that should be excluded)
    if copilot.schema_json_exists:
        _check_noise_fields(model, copilot.schema_json, findings)

    # Hidden field conflicts with verified answers
    if copilot.verified_answers and model.tables:
        _check_hidden_field_conflicts(model, copilot.verified_answers, findings)

    return findings


def _check_noise_fields(
    model: SemanticModel, schema: dict, findings: list[Finding]
) -> None:
    """Flag ID/sort-helper columns that are still visible in the AI schema."""
    noise_patterns = {"id", "key", "sk", "fk", "sort", "order", "idx"}

    for table in model.tables:
        for col in table.columns:
            col_lower = col.name.lower().replace(" ", "").replace("_", "")
            is_noise = any(p in col_lower for p in noise_patterns)
            if is_noise and not col.is_hidden:
                findings.append(Finding(
                    category=Category.AI_PREPARATION,
                    check="noise_fields_excluded",
                    severity=Severity.HIGH,
                    object=f"{table.name}.{col.name}",
                    object_type=ObjectType.COLUMN,
                    message=f"Column '{col.name}' looks like an ID/sort/key column and should be hidden from the AI schema.",
                    auto_fixable=True,
                ))


def _check_hidden_field_conflicts(
    model: SemanticModel, verified_answers: list[dict], findings: list[Finding]
) -> None:
    """Flag verified answers that reference hidden columns (they fail silently)."""
    hidden_cols: set[str] = set()
    for table in model.tables:
        for col in table.columns:
            if col.is_hidden:
                hidden_cols.add(f"{table.name}.{col.name}")
                hidden_cols.add(col.name)

    for va in verified_answers:
        va_id = va.get("id", "unknown")
        va_str = str(va)
        for hidden in hidden_cols:
            if hidden in va_str:
                findings.append(Finding(
                    category=Category.AI_PREPARATION,
                    check="hidden_field_conflicts",
                    severity=Severity.MEDIUM,
                    object=f"VerifiedAnswer/{va_id}",
                    object_type=ObjectType.VERIFIED_ANSWER,
                    message=f"Verified answer '{va_id}' may reference hidden column '{hidden}'. This will fail silently.",
                    auto_fixable=False,
                ))
                break
