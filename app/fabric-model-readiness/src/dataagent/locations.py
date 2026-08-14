"""Where to actually go to do each thing.

The module's most-used feature, and the least glamorous. Fabric spreads a data
agent's configuration across several panes, and the model's Prep for AI settings
live in a different product entirely. Advice that says "configure the AI data
schema" without saying where is advice that costs someone ten minutes.

Paths are taken from Microsoft Learn rather than memory. Where a surface has both
a portal path and an SDK call, both are given: the portal for the person doing it
once, the SDK for the person doing it every release.
"""

from __future__ import annotations

from dataclasses import dataclass

FABRIC_DOCS = "https://learn.microsoft.com/en-us/fabric/data-science"
POWERBI_DOCS = "https://learn.microsoft.com/en-us/power-bi/create-reports"


@dataclass(frozen=True)
class Location:
    """One place a thing is configured."""

    what: str
    surface: str      # fabric-portal | power-bi-desktop | sdk
    path: str
    doc_url: str = ""
    note: str = ""


LOCATIONS: dict[str, Location] = {
    # -- creating and wiring the agent ---------------------------------------
    "create_agent": Location(
        what="Create a data agent",
        surface="fabric-portal",
        path="Workspace > + New item > All items > search 'Fabric data agent' > name it",
        doc_url=f"{FABRIC_DOCS}/how-to-create-data-agent",
    ),
    "add_data_source": Location(
        what="Add a data source",
        surface="fabric-portal",
        path="Data agent > Explorer (left pane) > + Data source > pick from the OneLake catalog > Add",
        doc_url=f"{FABRIC_DOCS}/how-to-create-data-agent",
        note="The catalog opens automatically the first time. Sources are added one at a time, five maximum.",
    ),
    "select_tables": Location(
        what="Choose which tables the agent can query",
        surface="fabric-portal",
        path="Data agent > Explorer (left pane) > expand the data source > tick the tables",
        doc_url=f"{FABRIC_DOCS}/how-to-create-data-agent",
        note="This is the selection that must match the Prep for AI schema.",
    ),
    "refresh_data_source": Location(
        what="Refresh a data source after the model changed",
        surface="fabric-portal",
        path="Data agent > Explorer > hover the source > ... > Refresh",
        doc_url=f"{FABRIC_DOCS}/how-to-create-data-agent",
    ),

    # -- agent-level configuration -------------------------------------------
    "agent_instructions": Location(
        what="Write the agent instructions",
        surface="fabric-portal",
        path="Data agent > Data agent instructions",
        doc_url=f"{FABRIC_DOCS}/how-to-create-data-agent",
        note="Up to 15,000 characters. Routing, formatting, abbreviations, and tone only.",
    ),
    "example_queries": Location(
        what="Add example query/question pairs",
        surface="fabric-portal",
        path="Data agent > Example queries > pick a data source > Add or Edit Example Queries (not offered for semantic models or ontologies)",
        doc_url=f"{FABRIC_DOCS}/how-to-create-data-agent",
        note="Up to 100 per data source. Power BI semantic models and ontologies are excluded entirely -- use verified answers for those.",
    ),
    "publish_agent": Location(
        what="Publish the agent",
        surface="fabric-portal",
        path="Data agent > Publish > enter a description",
        doc_url=f"{FABRIC_DOCS}/how-to-create-data-agent",
        note="Publishing creates a second version. The draft stays editable; colleagues query the published one.",
    ),
    "diagnostics": Location(
        what="Download diagnostics logs",
        surface="fabric-portal",
        path="Data agent > diagnostics button",
        doc_url=f"{FABRIC_DOCS}/evaluate-data-agent#diagnostics-button",
    ),

    # -- the model side, for the cross-references ----------------------------
    "prep_for_ai": Location(
        what="Open Prep data for AI",
        surface="power-bi-desktop",
        path="Power BI Desktop > Home ribbon > Prep data for AI",
        doc_url=f"{POWERBI_DOCS}/copilot-prep-semantic-model",
        note=(
            "Q&A must be enabled on the model or every tab in here is disabled. "
            "Requires Write permission; Read alone is enough to use the model in an agent. "
            "Import, DirectQuery, and Composite (local) connections only."
        ),
    ),
    "ai_data_schema": Location(
        what="Choose which tables, columns, and measures the AI can see",
        surface="power-bi-desktop",
        path="Power BI Desktop > Home ribbon > Prep data for AI > Simplify the data schema",
        doc_url=f"{POWERBI_DOCS}/copilot-prep-semantic-model",
        note="Written to Copilot/schema.json in the PBIP folder, which the Analyzer reads.",
    ),
    "ai_instructions": Location(
        what="Write the model's own AI instructions",
        surface="power-bi-desktop",
        path="Power BI Desktop > Home ribbon > Prep data for AI > AI instructions",
        doc_url=f"{POWERBI_DOCS}/copilot-prep-semantic-model",
        note=(
            "Model-specific guidance belongs here, not at agent level. "
            "Capped at 10,000 characters -- a different limit from the agent's 15,000."
        ),
    ),
    "verified_answers": Location(
        what="Create a verified answer",
        surface="power-bi-desktop",
        path="Select the visual you want to pin > three-dot menu on the visual header > Set up a verified answer",
        doc_url=f"{POWERBI_DOCS}/copilot-prep-semantic-model",
        note=(
            "Started from a visual, not from the Prep data for AI dialog. "
            "The semantic model equivalent of example queries."
        ),
    ),
    "evaluate_agent": Location(
        what="Evaluate the agent against ground truth",
        surface="sdk",
        path=(
            "%pip install -U fabric-data-agent-sdk; "
            "from fabric.dataagent.evaluation import evaluate_data_agent, get_evaluation_summary, "
            "get_evaluation_details"
        ),
        doc_url=f"{FABRIC_DOCS}/evaluate-data-agent",
        note="Takes a ground-truth DataFrame of question/expected-answer pairs and returns an evaluation id.",
    ),

    # -- code-first equivalents ----------------------------------------------
    "sdk_configure": Location(
        what="Configure the agent from code",
        surface="sdk",
        path="pip install fabric-data-agent-sdk; agent.update_settings(ai_instructions=...); agent.add_staging_datasource(...)",
        doc_url=f"{FABRIC_DOCS}/fabric-data-agent-sdk",
        note="Management plane over the Fabric REST API. Auth with AzureCliCredential or a service principal.",
    ),
    "sdk_publish": Location(
        what="Publish from code",
        surface="sdk",
        path="agent.publish_staging(description='...')",
        doc_url=f"{FABRIC_DOCS}/fabric-data-agent-sdk",
    ),
    "sdk_query": Location(
        what="Query a published agent",
        surface="sdk",
        path="MCP endpoint: https://api.fabric.microsoft.com/v1/mcp/workspaces/{workspaceId}/dataagents/{agentId}/agent",
        doc_url=f"{FABRIC_DOCS}/data-agent-mcp-server",
        note="Only works after publishing.",
    ),
}

# Which location answers which check.
CHECK_LOCATIONS: dict[str, str] = {
    "agent_tables_match_ai_schema": "select_tables",
    "agent_instructions_not_model_specific": "agent_instructions",
    "agent_instructions_length": "agent_instructions",
    "agent_instructions_present": "agent_instructions",
    "agent_datasource_count": "add_data_source",
    "agent_description_present": "publish_agent",
    "agent_publish_drift": "publish_agent",
    "agent_example_queries_unavailable": "verified_answers",
    "agent_lifecycle_managed": "publish_agent",
}


def location_for(check: str) -> Location | None:
    key = CHECK_LOCATIONS.get(check)
    return LOCATIONS.get(key) if key else None


def as_dict(location: Location) -> dict:
    return {
        "what": location.what,
        "surface": location.surface,
        "path": location.path,
        "doc_url": location.doc_url,
        "note": location.note,
    }
