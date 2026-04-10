"""Shared fixtures for all test modules."""

from __future__ import annotations

import pytest

from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    RelationshipInfo,
    RoleInfo,
    SemanticModel,
    TableInfo,
)


def make_model(
    tables: list[TableInfo] | None = None,
    relationships: list[RelationshipInfo] | None = None,
    roles: list[RoleInfo] | None = None,
    copilot: CopilotConfig | None = None,
    name: str = "TestModel",
) -> SemanticModel:
    """Build a SemanticModel with sensible defaults for testing."""
    return SemanticModel(
        name=name,
        path="./test",
        format=ModelFormat.TMSL,
        tables=tables or [],
        relationships=relationships or [],
        roles=roles or [],
        copilot=copilot or CopilotConfig(),
    )
