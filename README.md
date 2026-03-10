# Fabric Semantic Model AI Readiness

Analyze Power BI semantic models against Microsoft's "Prep for AI" best practices, fix issues, and track changes over time.

Works as a **standalone desktop app** for scanning and reviewing models, or as a **Claude Code-powered multi-agent system** for automated remediation via the Power BI Modeling MCP Server.

## What It Does

| Capability | Desktop App | With Claude Code |
|---|---|---|
| Scan a PBIP/PBIX model and get a readiness score (0-100) | Yes | Yes |
| Review findings grouped by severity with fix recommendations | Yes | Yes |
| Accept/reject/defer individual findings | Yes | Yes |
| Browse change history with grouped, filterable views | Yes | Yes |
| Apply accepted changes live to Power BI Desktop via MCP | -- | Yes |
| AI-generated change descriptions and session recording | -- | Yes |
| Drift detection (regressions from previous fixes) | -- | Yes |

### Readiness Score

The scanner checks six categories weighted by importance to Copilot:

| Category | Weight | What It Checks |
|---|---|---|
| AI Preparation | 25% | Schema visibility, instructions, verified answers |
| Metadata Completeness | 25% | Descriptions, synonyms, data categories |
| Schema Design | 20% | Star schema, naming, display folders, hidden keys |
| Measures & Calculations | 15% | Explicit DAX, time intelligence, qualified refs |
| Relationships | 10% | Connectivity, cardinality, no ambiguity |
| Data Types & Aggregation | 5% | Correct types, summarization settings |

| Score | Rating |
|---|---|
| 90--100 | AI-Ready |
| 75--89 | Mostly Ready |
| 50--74 | Needs Work |
| 0--49 | Not Ready |

---

## Install (Desktop App)

### Prerequisites

- **Windows 10/11** (x64)
- **Python 3.12+** -- [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** -- [nodejs.org](https://nodejs.org/)
- **Git** -- [git-scm.com](https://git-scm.com/)

### Build the Installer

```powershell
git clone https://github.com/COMPANY/fabric-model-readiness.git
cd fabric-model-readiness

.\build.ps1
```

This takes a few minutes. It:
1. Installs Python dependencies and bundles the backend into a standalone `.exe` via PyInstaller
2. Builds the React frontend
3. Packages everything into a Windows installer via electron-builder

When finished, the installer is at:
```
app\release\Fabric Model AI Readiness Setup *.exe
```

Run the installer. The app launches with everything bundled -- no Python or Node.js needed on the target machine.

### Run in Development Mode

If you want to develop or debug instead of building an installer:

```powershell
# Terminal 1: start the Python backend
cd fabric-model-readiness
pip install -e .
cd src
python -m api.server --port 8000

# Terminal 2: start the Electron + Vite dev server
cd app
npm install
npm run dev:electron
```

Or use the shortcut script (starts both):
```powershell
.\dev.ps1
```

The Electron app opens with hot-reload. The Python backend runs on port 8000.

---

## Usage (Desktop App)

1. **Open the app** and drag a `.SemanticModel` folder (PBIP) or `.pbix` file onto the drop zone
2. **Review the score** and findings grouped by severity
3. **Accept, reject, or defer** each finding
4. **Click Apply** to record your decisions
5. **View History** to browse past sessions with category grouping, filters, and search

The desktop app handles scanning, reviewing, and history. To actually *apply* changes to a live Power BI model, see the Claude Code section below.

---

## Claude Code Setup (Full Experience)

Claude Code adds three AI agents that can analyze models conversationally and apply changes live to Power BI Desktop.

### Prerequisites (in addition to the above)

- **Claude Code** -- [Anthropic CLI](https://docs.anthropic.com/en/docs/claude-code)
- **Power BI Desktop** -- with the target model open

### Setup

1. Clone the repo and open it in Claude Code:
   ```powershell
   cd fabric-model-readiness
   claude
   ```

2. Claude Code automatically picks up `.mcp.json` (configures the Power BI Modeling MCP Server) and `.claude/skills/` (the three agent skills).

3. **Download the MCP server** (not included in the repo due to size):
   - Download the [Power BI Modeling MCP VSIX](https://marketplace.visualstudio.com/items?itemName=analysis-services.powerbi-modeling-mcp) (win32-x64)
   - Rename `.vsix` to `.zip` and extract to `tools/powerbi-modeling-mcp/extracted/`
   - Update the absolute path in `.mcp.json` if needed

### Agent Skills

**`/scout`** -- Read-only analyzer
```
/scout ./path/to/MyModel.SemanticModel/
```
Scans the model and produces a findings report with a readiness score. Strictly read-only.

**`/enforcer`** -- Change applier
```
/enforcer
```
Reads the latest Scout findings, proposes changes, and applies accepted changes live to Power BI Desktop via the MCP server. Prompts before every change.

**`/historian`** -- Change tracker
```
/historian log --model "MyModel"
/historian summary
/historian drift
```
Records all changes proposed/accepted/rejected/deferred. Append-only changelog with drift detection.

### Typical Workflow

```
/scout ./MyModel.SemanticModel/     # Analyze the model
                                     # Review findings in the terminal or GUI
/enforcer                            # Apply accepted changes to Power BI Desktop
/historian log                       # View the change log
```

---

## Project Structure

```
.
├── fabric-model-readiness/        # Python backend
│   ├── src/
│   │   ├── api/                   #   FastAPI server + routes
│   │   ├── scout/                 #   Scanner rules + scoring
│   │   ├── enforcer/              #   Change planner + file applier
│   │   ├── historian/             #   Logger, drift detection, resurfacing
│   │   └── shared/                #   Pydantic models, config
│   ├── pyproject.toml
│   └── pyinstaller.spec
├── app/                           # Electron desktop app
│   ├── electron/                  #   Main process, Python backend manager
│   ├── frontend/                  #   React + Tailwind UI
│   │   └── src/
│   │       ├── components/        #     DropZone, FindingsPanel, HistoryView, etc.
│   │       ├── hooks/             #     useApi, useScan, useDecisions
│   │       └── types/             #     TypeScript interfaces
│   ├── package.json
│   └── electron-builder.yml
├── .claude/skills/                # Claude Code skill definitions
│   ├── scout/SKILL.md
│   ├── enforcer/SKILL.md
│   └── historian/SKILL.md
├── .mcp.json                      # MCP server config (Power BI Modeling)
├── tools/powerbi-modeling-mcp/    # Bundled MCP server executable
├── findings/                      # Scout scan results (JSON)
├── reports/                       # Human-readable markdown reports
├── .history/                      # Historian changelogs (JSON, append-only)
├── Power BI Standards.md          # Organizational standards reference
├── build.ps1                      # Production build script
├── dev.ps1                        # Development mode launcher
└── CLAUDE.md                      # Claude Code project instructions
```

---

## Key Standards

The scanner enforces both Microsoft's Copilot preparation guidelines and organizational standards from `Power BI Standards.md`:

- Star schema required (no flat tables or snowflakes)
- Fact tables hidden from users
- Surrogate keys hidden on dimension tables
- Display folders required for all columns and measures
- All aggregations as explicit DAX measures
- Fully qualified column references in DAX
- Date table marked as date table; no auto-generated date tables
- RLS roles defined (minimum Admin and General)
- USERELATIONSHIP preferred over duplicating dimension tables
- No bi-directional relationships (use CROSSFILTER in DAX)

When a Microsoft recommendation conflicts with an organizational standard, the organizational standard takes precedence.

---

## References

| Topic | Link |
|---|---|
| Copilot: Prepare Semantic Model | [learn.microsoft.com](https://learn.microsoft.com/en-us/power-bi/create-reports/tutorial-copilot-power-bi-prepare-model) |
| Optimize Semantic Model for Copilot | [learn.microsoft.com](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-evaluate-data) |
| Semantic Model Best Practices for Data Agent | [learn.microsoft.com](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices) |
| Power BI MCP Servers Overview | [learn.microsoft.com](https://learn.microsoft.com/en-us/power-bi/developer/mcp/mcp-servers-overview) |
| Modeling MCP Server (GitHub) | [github.com/microsoft/powerbi-modeling-mcp](https://github.com/microsoft/powerbi-modeling-mcp) |
| Q&A Linguistic Schema | [learn.microsoft.com](https://learn.microsoft.com/en-us/power-bi/natural-language/q-and-a-tooling-advanced) |
| PBIP Folder Structure | [learn.microsoft.com](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset) |
