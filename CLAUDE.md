# Fabric Semantic Model AI Readiness

Multi-agent system that analyzes Power BI semantic models (PBIP/PBIX) for Microsoft's "Prep for AI" best practices, proposes remediations, and tracks change history over time.

**The most important rule:** Never modify a semantic model file without explicit user approval.

## Quick Start

```bash
# Analyze a PBIP project
/scout ./MyModel.SemanticModel/

# Analyze a PBIX file (extracts to temp PBIP first)
/scout ./MyReport.pbix

# Review proposed changes and record decisions (CLI)
enforcer review --model "MyModel"

# Apply accepted changes to Power BI Desktop via MCP (Claude Code)
/enforcer

# View change history
/historian log
/historian log --model "MyModel"
```

**Applying changes:** The `/enforcer` skill in Claude Code connects to Power BI Desktop via the Power BI Modeling MCP Server and applies accepted changes live. Power BI Desktop must be running with the target model open.

## Architecture: Three Agents

| Skill | Role | Key Constraint |
|-------|------|----------------|
| `/scout` | Read-only analyzer. Scans PBIP/PBIX and produces a findings report with readiness score. | **Strictly read-only** -- never writes to model files. |
| `/enforcer` | Change applier. Consumes Scout findings, proposes changes, applies via Claude Code + Power BI Modeling MCP Server connected to Power BI Desktop. | **Must prompt before every change** -- no silent modifications. |
| `/historian` | Change tracker. Records all changes proposed/accepted/rejected/deferred. | **Append-only** -- never deletes or overwrites historical entries. |

Each skill has detailed instructions in `.claude/skills/[name]/SKILL.md`.

## Standards Reference

**`Power BI Standards.md`** is the authoritative standards document for this organization's Power BI practices. It covers data modeling, Power Query, DAX, reports, security, and deployment conventions.

- When Scout rules detect an issue, check whether `Power BI Standards.md` has a relevant standard. If it does, cite the standard in the finding's recommendation.
- When Enforcer proposes a change, the proposal must comply with `Power BI Standards.md`. If a Microsoft "Prep for AI" recommendation conflicts with an organizational standard, **defer to `Power BI Standards.md`** and note the conflict.
- Key standards that overlap with Scout checks:
  - **Star schema required** -- no flat tables or snowflakes (Data Modeling > Star Schemas)
  - **Fact tables hidden** from users; only surrogate keys + fact columns (Data Modeling > Fact Tables)
  - **Surrogate keys hidden** on dimension tables (Data Modeling > Dimension Tables)
  - **Display folders required** for columns and measures (Data Modeling > Dimension Tables, DAX)
  - **No default aggregations** -- all aggregations must be explicit DAX measures (DAX)
  - **Measure tables** -- all measures stored in dedicated measure tables (DAX)
  - **Fully qualified column references** -- always `'Table'[Column]`, never unqualified (DAX)
  - **No float data types** unless necessary (Data Modeling > General)
  - **Date table marked** as date table; no auto-generated date tables (Data Modeling > Dates)
  - **RLS roles defined** -- at minimum Admin and General (Security and Sharing)
  - **`USERELATIONSHIP`** preferred over duplicating dimension tables (Data Modeling > Dimension Tables, Dates)
  - **No bi-directional relationships** -- use `CROSSFILTER` in DAX instead (Data Modeling > Star Schemas, DAX)

## MCP Server Setup (Enforcer)

The Enforcer applies changes via the **[Power BI Modeling MCP Server](https://github.com/microsoft/powerbi-modeling-mcp)** (official Microsoft tool, public preview), configured in `.mcp.json` at the project root.

**Installation:**
1. The server executable is bundled at `tools/powerbi-modeling-mcp/extracted/extension/server/powerbi-modeling-mcp.exe` (extracted from the [VS Marketplace extension](https://marketplace.visualstudio.com/items?itemName=analysis-services.powerbi-modeling-mcp) v0.4.0).
2. `.mcp.json` already points to this path. If you move the project, update the absolute path in `.mcp.json`.
3. To update to a newer version: download the VSIX from the VS Marketplace for `win32-x64`, rename to `.zip`, extract, and replace the contents of `tools/powerbi-modeling-mcp/extracted/`.

**Usage:**
1. Open Power BI Desktop with the target semantic model loaded
2. Start a Claude Code session from this project root (it picks up `.mcp.json` automatically)
3. Run `/enforcer` -- it connects to Desktop via the MCP server and applies accepted changes live

**Connection:** The MCP server connects to Power BI Desktop, Fabric workspaces, or PBIP files. For Desktop, the Enforcer sends a natural language connection command like `Connect to '[File Name]' in Power BI Desktop`. Credentials are handled via the Azure Identity SDK -- no service principal or manual token management needed.

Claude Code manages the MCP connection lifecycle. No Python MCP client is needed.

## Critical Rules

- No emojis unless necessary
- Never make things up -- ask if unsure
- All agent output must be deterministic and reproducible given the same input
- Use `.scratch/` for ephemeral working files (temp extractions, intermediate JSON)
- Always preserve the original PBIP folder structure when writing changes

## PBIP File Structure Reference

The Scout reads these paths within a PBIP project:

```
SemanticModel/
  definition.pbism                  # Model definition settings (version determines TMSL vs TMDL)
  model.bim                         # TMSL format -- single JSON, all model metadata
  definition/                       # TMDL format -- one file per object (preferred for Git)
    [Tables]/
    [Perspectives]/
    [Roles]/
    [Cultures]/
  Copilot/
    Instructions/
      instructions.md               # AI instructions (business context, terminology)
    VerifiedAnswers/
      definitions/
        [answer-id]/
          definition.json           # Trigger phrases + visual config
          filters.json
          visualSource.json
    schema.json                     # AI data schema (field visibility + synonyms)
    settings.json                   # Copilot settings
    examplePrompts.json             # Zero Prompt examples
  diagramLayout.json
  .platform
```

**TMSL vs TMDL:** Check `definition.pbism` > `version`. Version `1.0` = TMSL (`model.bim`). Version `4.0+` = TMDL (`definition/` folder). The Scout must handle both formats.

**PBIX handling:** PBIX is a compressed binary. Extract to a temp PBIP structure before analysis. Never modify PBIX directly.

## Readiness Score Calculation

The Scout produces a 0-100 score. Weights by category:

| Category | Weight |
|----------|--------|
| AI Preparation (schema, instructions, verified answers) | 25% |
| Metadata Completeness (descriptions, synonyms, data categories) | 25% |
| Schema Design (star schema, naming, normalization) | 20% |
| Measures and Calculations (explicit DAX, time intelligence) | 15% |
| Relationships (connectivity, cardinality, no ambiguity) | 10% |
| Data Types and Aggregation (correct types, summarization) | 5% |

**Within each category:** Score = (passing checks / total checks) * weight. Critical failures apply a 2x penalty (count as two failed checks).

| Score Range | Rating |
|-------------|--------|
| 90-100 | AI-Ready |
| 75-89 | Mostly Ready (minor gaps) |
| 50-74 | Needs Work (significant gaps) |
| 0-49 | Not Ready (fundamental issues) |

## Common Pitfalls

### Description Length Truncation

Copilot only reads the **first 200 characters** of any description (table, column, measure, calculation group). Front-load the most important information.

```
// WRONG - important info buried after 200 chars
"This column stores the identifier for each individual customer record
in our system and is generated automatically by the CRM platform when
a new customer is onboarded. Use this for joins to FactSales."

// CORRECT - key info first
"Unique customer identifier (CRM-generated). Primary key for joins
to FactSales, FactReturns, and FactSupport tables."
```

### Hidden Fields in Verified Answers

Verified answers that reference hidden columns **fail silently**. The Scout must cross-reference verified answer definitions against hidden field lists.

### Duplicate Synonyms Across Columns

Adding the same synonym to multiple columns creates ambiguity. For example, "revenue" as a synonym on both `FactSales.Amount` and `FactSales.NetAmount` makes Copilot guess.

### AI Instructions vs Data Agent Instructions

The DAX generation tool **only uses Prep for AI instructions** (from `Copilot/Instructions/instructions.md`). Data-agent-level instructions are ignored for DAX generation. The Scout should flag if critical business context is only in data agent instructions but missing from model-level instructions.

### Measure Dependencies

Before hiding or excluding any column/table from the AI schema, check if visible measures depend on it. Use dependency analysis to trace the full chain. A hidden column referenced by a visible measure must remain accessible.

## File Conventions

```
.claude/skills/              # Skill definitions (Scout, Enforcer, Historian)

.scratch/                    # Ephemeral working files (gitignored)
  extractions/               # Temp PBIX -> PBIP extractions
  scan-results/              # Scout output JSON
  enforcer-session.json      # Enforcer -> Historian handoff

.history/                    # Historian changelog (committed to source control)
  [model-name].json          # Per-model change history

findings/                    # Scout reports (committed)
  [model-name]/
    [scan-id].json           # Individual scan results
    latest.json              # Symlink to most recent scan

reports/                     # Human-readable markdown reports (committed)
  [model-name]/
    [YYYY-MM-DD]-scan-[short-id].md        # Scout findings report
    [YYYY-MM-DD]-enforcer-[short-id].md    # Enforcer decisions report
    [YYYY-MM-DD]-history.md                # Cumulative history (overwritten each session)
```

## Git Workflow

```bash
git checkout -b scan/my-model-YYYY-MM-DD
```

- Commit scan results and change history together
- PR description should include pre/post readiness score
- Never commit `.scratch/` contents
- Always commit `.history/` updates

## Key Microsoft References

| Topic | Reference |
|-------|-----------|
| Prep for AI overview | [Copilot: Prepare Semantic Model](https://learn.microsoft.com/en-us/power-bi/create-reports/tutorial-copilot-power-bi-prepare-model) |
| Optimization checklist | [Optimize Semantic Model for Copilot](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-evaluate-data) |
| Data agent best practices | [Semantic Model Best Practices for Data Agent](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices) |
| PBIP folder structure | [Power BI Desktop Project: Semantic Model Folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset) |
| Linguistic schema & synonyms | [Q&A Linguistic Schema and Phrasings](https://learn.microsoft.com/en-us/power-bi/natural-language/q-and-a-tooling-advanced) |
| Q&A best practices (applies to Copilot) | [Best Practices to Optimize Q&A](https://learn.microsoft.com/en-us/power-bi/natural-language/q-and-a-best-practices) |
| Power BI MCP servers overview | [MCP Servers for Power BI](https://learn.microsoft.com/en-us/power-bi/developer/mcp/mcp-servers-overview) |
| Modeling MCP server (GitHub) | [microsoft/powerbi-modeling-mcp](https://github.com/microsoft/powerbi-modeling-mcp) |
