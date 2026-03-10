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
# API Server
# ---------------------------------------------------------------------------

API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "0"))  # 0 = pick random available port
