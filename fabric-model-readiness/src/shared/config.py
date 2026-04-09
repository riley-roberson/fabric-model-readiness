"""Project-wide configuration loaded from environment variables and .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRATCH_DIR = PROJECT_ROOT / ".scratch"
HISTORY_DIR = PROJECT_ROOT / ".history"
FINDINGS_DIR = PROJECT_ROOT / "findings"

SCRATCH_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)
FINDINGS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Anthropic API
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL_FAST: str = "claude-sonnet-4-5-20250929"
LLM_MODEL_REASONING: str = "claude-opus-4-6"

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------

CATEGORY_WEIGHTS: dict[str, float] = {
    "ai_preparation": 0.20,
    "metadata_completeness": 0.20,
    "schema_design": 0.15,
    "measures": 0.15,
    "relationships": 0.10,
    "data_types": 0.05,
    "data_consistency": 0.05,
    "org_standards": 0.10,
}

CRITICAL_PENALTY_MULTIPLIER: int = 2

# ---------------------------------------------------------------------------
# Check-to-profile mapping (single source of truth for profile filtering)
# Tags: "ai" = Microsoft Prep-for-AI checks, "org" = organizational standards,
#        "both" = shared checks included in every profile.
# ---------------------------------------------------------------------------

CHECK_PROFILES: dict[str, str] = {
    # Schema design
    "table_naming": "both",
    "column_naming": "both",
    "measure_naming": "both",
    "wide_table_detection": "both",
    "fact_table_hidden": "both",
    "surrogate_key_hidden": "both",
    "cross_table_disambiguation": "ai",
    # Metadata completeness
    "table_descriptions": "ai",
    "column_descriptions": "ai",
    "measure_descriptions": "ai",
    "data_categories": "ai",
    "synonyms": "ai",
    # Relationships
    "missing_relationships": "ai",
    "inactive_relationships": "both",
    "cardinality_correctness": "both",
    "bidirectional_relationship": "org",
    "ambiguous_paths": "both",
    # Measures and calculations
    "helper_measures_exposed": "ai",
    "time_intelligence": "ai",
    "duplicate_measures": "both",
    "measure_table_required": "org",
    "direct_measure_reference": "org",
    "fully_qualified_columns": "org",
    "shortened_calculate": "org",
    "iferror_usage": "org",
    "nested_if": "org",
    "use_divide_function": "org",
    # AI preparation
    "ai_schema_configured": "ai",
    "ai_instructions_present": "ai",
    "ai_instructions_quality": "ai",
    "verified_answers": "ai",
    "verified_answer_quality": "ai",
    "noise_fields_excluded": "ai",
    "hidden_field_conflicts": "ai",
    # Data types and aggregation
    "default_summarization": "both",
    "sort_by_column": "ai",
    "avoid_float_types": "org",
    # Data consistency
    "partitioned_tables": "org",
    # Organizational standards
    "column_display_folders": "org",
    "measure_display_folders": "org",
    "rls_roles_defined": "org",
    "rls_admin_role": "org",
    "rls_general_role": "org",
    "date_table_marked": "org",
    "userelationship_preferred": "org",
}

# ---------------------------------------------------------------------------
# API Server
# ---------------------------------------------------------------------------

API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "0"))  # 0 = pick random available port
