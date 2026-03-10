"""Shared data classes used across all three agents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    SCHEMA_DESIGN = "schema_design"
    METADATA_COMPLETENESS = "metadata_completeness"
    DATA_TYPES = "data_types"
    RELATIONSHIPS = "relationships"
    MEASURES = "measures"
    AI_PREPARATION = "ai_preparation"
    DATA_CONSISTENCY = "data_consistency"
    ORG_STANDARDS = "org_standards"


class ModelFormat(str, Enum):
    TMSL = "TMSL"
    TMDL = "TMDL"


class Disposition(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ObjectType(str, Enum):
    TABLE = "table"
    COLUMN = "column"
    MEASURE = "measure"
    RELATIONSHIP = "relationship"
    COPILOT_SCHEMA = "copilot_schema"
    COPILOT_INSTRUCTIONS = "copilot_instructions"
    VERIFIED_ANSWER = "verified_answer"
    MODEL = "model"


# ---------------------------------------------------------------------------
# Scout models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"f-{uuid.uuid4().hex[:6]}")
    category: Category
    check: str
    severity: Severity
    object: str
    object_type: ObjectType
    message: str
    recommendation: str = ""
    auto_fixable: bool = False


class ScanSummary(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    score: float = 0.0


class ScanReport(BaseModel):
    scan_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    model_path: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    format: ModelFormat
    summary: ScanSummary = Field(default_factory=ScanSummary)
    findings: list[Finding] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Enforcer models
# ---------------------------------------------------------------------------

class ChangeProposal(BaseModel):
    finding_id: str
    category: Category
    severity: Severity
    object: str
    object_type: ObjectType
    title: str
    why: str
    change_description: str
    impact: str | None = None
    auto_fixable: bool = False
    proposed_value: Any = None


class ChangeDecision(BaseModel):
    finding_id: str
    disposition: Disposition
    reason: str | None = None
    edited_value: Any = None


class ChangePlan(BaseModel):
    model_name: str
    scan_id: str
    pre_score: float
    proposals: list[ChangeProposal] = Field(default_factory=list)
    decisions: list[ChangeDecision] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Historian models
# ---------------------------------------------------------------------------

class ChangeRecord(BaseModel):
    finding_id: str
    category: Category
    object: str
    action: Disposition
    description: str = ""
    before: Any = None
    after: Any = None
    reason: str | None = None


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scan_id: str
    pre_score: float
    post_score: float | None = None
    changes: list[ChangeRecord] = Field(default_factory=list)


class ModelHistory(BaseModel):
    model_name: str
    sessions: list[Session] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsed semantic model (in-memory representation used by Scout)
# ---------------------------------------------------------------------------

class ColumnInfo(BaseModel):
    name: str
    table: str
    data_type: str = ""
    description: str = ""
    is_hidden: bool = False
    synonyms: list[str] = Field(default_factory=list)
    data_category: str = ""
    summarize_by: str = ""
    sort_by_column: str = ""
    display_folder: str = ""


class MeasureInfo(BaseModel):
    name: str
    table: str
    expression: str = ""
    description: str = ""
    is_hidden: bool = False
    display_folder: str = ""


class RelationshipInfo(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    is_active: bool = True
    cardinality: str = ""
    cross_filter_direction: str = ""


class TableInfo(BaseModel):
    name: str
    description: str = ""
    columns: list[ColumnInfo] = Field(default_factory=list)
    measures: list[MeasureInfo] = Field(default_factory=list)
    is_hidden: bool = False
    is_date_table: bool = False


class RoleInfo(BaseModel):
    name: str
    filter_expressions: list[str] = Field(default_factory=list)


class CopilotConfig(BaseModel):
    schema_json_exists: bool = False
    schema_json: dict = Field(default_factory=dict)
    instructions_exist: bool = False
    instructions_content: str = ""
    verified_answers: list[dict] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class SemanticModel(BaseModel):
    name: str
    path: str
    format: ModelFormat
    tables: list[TableInfo] = Field(default_factory=list)
    relationships: list[RelationshipInfo] = Field(default_factory=list)
    roles: list[RoleInfo] = Field(default_factory=list)
    copilot: CopilotConfig = Field(default_factory=CopilotConfig)
