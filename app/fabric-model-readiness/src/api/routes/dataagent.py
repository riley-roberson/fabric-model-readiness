"""Data Agent Developer API.

GET  /api/dataagent/advise        what to do about this agent, in order
POST /api/dataagent/advise        the same, given a known agent configuration
GET  /api/dataagent/instructions  a scoped agent-instruction draft
GET  /api/dataagent/locations     where everything is configured
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dataagent.advisor import advise, instructions_draft
from dataagent.config import AgentConfig, AgentDataSource
from dataagent.locations import LOCATIONS, as_dict
from scout import parser

router = APIRouter(prefix="/api/dataagent", tags=["dataagent"])


class DataSourceInput(BaseModel):
    name: str
    kind: str = "semantic_model"
    selected_tables: list[str] = []
    instructions: str = ""
    example_queries: int = 0


class AdviseRequest(BaseModel):
    model_path: str
    # Everything below is optional: the useful checks work on pasted-in config,
    # so none of this should require a Fabric connection.
    agent_name: str = ""
    description: str = ""
    instructions: str = ""
    data_sources: list[DataSourceInput] = []
    published: bool | None = None
    has_unpublished_changes: bool | None = None
    git_integration: bool | None = None


def _parse(model_path: str):
    try:
        return parser.parse(Path(model_path))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not parse the model: {exc}") from exc


def _config(request: AdviseRequest) -> AgentConfig:
    return AgentConfig(
        name=request.agent_name,
        description=request.description,
        instructions=request.instructions,
        data_sources=[
            AgentDataSource(
                name=s.name,
                kind=s.kind,
                selected_tables=list(s.selected_tables),
                instructions=s.instructions,
                example_queries=s.example_queries,
            )
            for s in request.data_sources
        ],
        published=request.published,
        has_unpublished_changes=request.has_unpublished_changes,
        git_integration=request.git_integration,
        source="manual",
    )


@router.get("/advise")
async def advise_without_config(model_path: str) -> dict:
    """What to set up, for a model with no agent configured yet."""
    return advise(_parse(model_path))


@router.post("/advise")
async def advise_with_config(request: AdviseRequest) -> dict:
    """The same, plus everything checkable about a known agent configuration."""
    return advise(_parse(request.model_path), _config(request))


@router.get("/instructions")
async def draft_instructions(model_path: str, other_sources: str = "") -> dict:
    """A scoped starting point for the agent's own instructions.

    Deliberately contains no model internals -- that guidance belongs in the
    model's AI instructions, and putting it here is the mistake the checklist
    calls out as very important to avoid.
    """
    model = _parse(model_path)
    sources = [s.strip() for s in other_sources.split(",") if s.strip()]
    text = instructions_draft(model, sources)
    return {
        "instructions": text,
        "characters": len(text),
        "where": as_dict(LOCATIONS["agent_instructions"]),
    }


@router.get("/locations")
async def all_locations() -> dict:
    """Every configuration surface, so the UI can link straight to it."""
    return {key: as_dict(loc) for key, loc in LOCATIONS.items()}
