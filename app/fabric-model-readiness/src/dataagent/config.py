"""The shape of a Fabric data agent's configuration.

Deliberately a plain dataclass rather than an SDK type. The same structure can be
filled three ways:

  * read from Fabric through fabric-data-agent-sdk (needs auth),
  * pasted in by hand from the portal (needs nothing),
  * left empty, in which case the checks report what is unknown rather than
    guessing.

That matters because the two rules the checklist marks *very important* are both
checkable from the instructions text and the selected table list alone. Neither
needs a tenant, so neither should be gated behind one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Stated limits, from the Fabric data agent documentation.
MAX_DATA_SOURCES = 5
MAX_INSTRUCTION_CHARS = 15_000
MAX_EXAMPLE_QUERIES_PER_SOURCE = 100

# A best practice rather than an enforced limit: "For optimal results, limit the
# number of tables to 25 or fewer for a given data source."
RECOMMENDED_MAX_TABLES_PER_SOURCE = 25

# The model's own AI instructions have a *different*, smaller cap than the
# agent's. Confusing the two is easy and the failure is silent truncation.
MAX_MODEL_AI_INSTRUCTION_CHARS = 10_000

# Example query/question pairs are not offered for these source types.
NO_EXAMPLE_QUERY_SUPPORT = {"semantic_model", "ontology"}


@dataclass
class AgentDataSource:
    name: str
    kind: str = "semantic_model"   # semantic_model | lakehouse | warehouse | kql | ontology | graph
    selected_tables: list[str] = field(default_factory=list)
    instructions: str = ""
    example_queries: int = 0

    @property
    def supports_example_queries(self) -> bool:
        return self.kind not in NO_EXAMPLE_QUERY_SUPPORT


@dataclass
class AgentConfig:
    """What we know about the agent. Empty fields mean unknown, not absent."""

    name: str = ""
    description: str = ""
    instructions: str = ""
    data_sources: list[AgentDataSource] = field(default_factory=list)
    published: bool | None = None
    has_unpublished_changes: bool | None = None
    git_integration: bool | None = None
    source: str = "manual"          # manual | sdk
    workspace: str = ""

    @property
    def is_known(self) -> bool:
        """True when there is enough here to check anything at all."""
        return bool(self.instructions or self.data_sources or self.description)

    def semantic_model_source(self, model_name: str) -> AgentDataSource | None:
        """The data source corresponding to a given semantic model, if present."""
        target = model_name.strip().lower()
        for source in self.data_sources:
            if source.kind == "semantic_model" and source.name.strip().lower() == target:
                return source
        # Fall back to the only semantic model, when there is exactly one.
        models = [s for s in self.data_sources if s.kind == "semantic_model"]
        return models[0] if len(models) == 1 else None
