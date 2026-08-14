# Modeling Studio

Three modules over one shared model parser and rule engine.

| Module | Question it answers | Where its truth lives |
|---|---|---|
| **S**emantic Model **S**idekick | *Am I following the process?* | `sidekick.json` + the process document |
| **A**I Readiness **A**nalyzer | *Is the model ready?* | The `.SemanticModel` folder on disk |
| **D**ata Agent **D**eveloper | *Is the agent built well?* | **Fabric — nothing on disk** |

That last row is the whole design problem, and the reason this module is
suggestion-heavy rather than lint-heavy: the Analyzer reads files, and the Data
Agent Developer has no files to read.

---

# Part 1 — Data Agent Developer

## What it is for

The Analyzer stops at the edge of the `.SemanticModel` folder. Everything after
that — which tables the agent exposes, what its instructions say, whether it has
been published, whether its answers are right — happens in Fabric and is
currently invisible to us.

It is also where the **18 unscored manual checklist items already live**: the
6 under *Data Agent Configuration* and the 12 under *Testing and Validation*.
Those were deliberately excluded from the Analyzer's score because they are not
observable in a model folder. They are exactly this module's remit.

## Two tiers, because of the constraint

### Tier 1 — Advisor (no Fabric connection)

Everything derivable from the model the Analyzer has already parsed. No auth, no
tenant, works offline. This is the suggestion-heavy core.

| Output | Built from | Why it matters |
|---|---|---|
| **Table selection list** | `Copilot/schema.json` | The checklist's *very important* rule is that the agent's selected tables match the Prep for AI schema exactly. We know that list; hand it over as something to tick off in the Explorer. |
| **Draft agent instructions** | Model + routing needs | Scoped deliberately narrow — see below. |
| **Test question set** | Verified answer triggers, measure names, date columns | Feeds *Testing and Validation*, which has no starting material today. |
| **Readiness gate** | The Analyzer's score | "This model scores 34. Fix these six things before you attach it to an agent." Connects the modules. |
| **Where to find it** | — | Every suggestion carries its exact location: portal path or Desktop menu. |

### Tier 2 — Connected (Fabric SDK)

`fabric-data-agent-sdk` on PyPI is a management-plane client over the Fabric
public REST API: `create_data_agent`, `update_settings(ai_instructions=…)`,
`add_staging_datasource(...)`, `publish_staging(description=…)`. Auth is
`AzureCliCredential` or a service principal. So the agent's configuration **is**
readable and writable — this does not have to stay advisory.

## The insight that makes this more than a doc summary

The checklist contains two rules marked *very important*, and both are
**cross-references between the agent and the model**. We hold one side already:

1. **Agent tables must match the AI Data Schema.** Scout parses
   `Copilot/schema.json`; the SDK reports the agent's selected tables. Diff them.
2. **Do NOT put model-specific instructions at agent level.** Scout knows every
   table, column, and measure name in the model. Agent instructions are plain
   text. Scanning that text for model object names detects the violation
   directly.

Rule 2 also dictates how Tier 1 drafts instructions. Agent-level text is limited
to **response formatting, cross-source routing, common abbreviations, and tone**.
Anything model-specific belongs in the *model's* AI instructions, which the
Analyzer already checks. The module's job is to route each piece of guidance to
the right layer, and to say so when it finds guidance in the wrong one.

## Proposed checks

Tier 1 (offline, advisory):

| Check | Rule |
|---|---|
| `agent_model_not_ready` | Analyzer score below threshold, or unresolved critical findings, before the model is attached |
| `agent_instructions_draft_available` | Offer a scoped draft when none exists |
| `agent_test_set_available` | Offer generated test questions |

Tier 2 (connected):

| Check | Rule | Source |
|---|---|---|
| `agent_tables_match_ai_schema` | Selected tables ≡ Prep for AI schema | *very important* |
| `agent_instructions_not_model_specific` | No model object names in agent-level instructions | *very important* |
| `agent_instructions_length` | Within the **15,000 character** cap, and concise |  |
| `agent_datasource_count` | At most **5** data sources |  |
| `agent_description_present` | Description set before publishing — it guides colleagues *and* other orchestrators |  |
| `agent_publish_drift` | Draft and published versions have diverged |  |
| `agent_lifecycle_managed` | Git integration and deployment pipelines in use |  |

## Nuances the docs make explicit, and that a naive port would get wrong

- **Example queries are not supported for Power BI semantic models.** They work
  for lakehouse, warehouse, and KQL only. Suggesting them for a semantic-model
  agent would send someone hunting for a control that does not exist. For
  semantic models the equivalent lever is verified answers, which the Analyzer
  already covers.
- **Read permission is enough** to add a semantic model to an agent; Write is
  needed only to modify the model or use Prep for AI. Worth stating, because
  people over-request access here.
- **Five data sources is a hard cap**, in any combination.
- **Draft and published are two distinct versions.** Testing the draft and
  assuming colleagues see those answers is an easy and invisible mistake.

## ⚠ Time-critical, independent of this plan

The Fabric Data Agent SDK is moving from the **OpenAI Assistants API to the
Responses API**. Migration opened **11 August 2026**; the Assistants API
**deprecates 26 August 2026** — twelve days from now. Only querying code is
affected; create/configure/publish are unchanged. If anything here already
queries an agent through the Fabric OpenAI client, that is a this-week job, not
a this-project job.

## Build sequence

| Stage | Ships | Needs Fabric auth |
|---|---|---|
| **D1 — Advisor** | Table selection list, readiness gate, "where to find it" navigation, the 18 checklist items as a tracked surface | No |
| **D2 — Generators** | Scoped agent-instruction draft, test question set, layer-routing advice | No |
| **D3 — Connect** | SDK client, read agent config, `agent_*` checks incl. both *very important* cross-references | Yes |
| **D4 — Evaluate** | Query the published agent over its MCP endpoint with the generated test set; capture and review the generated DAX | Yes |
| **D5 — Write back** | Push instructions and table selection through the SDK, with the same backup/preview/rollback discipline as the model Enforcer | Yes |

D1 and D2 are useful alone and need no tenant access. D3 is where the module
stops being advisory. **D5 writes to a published artifact other people consume**
— it deserves more caution than the model Enforcer, not less.

## Fit with the other two modules

- The Sidekick's proposed **AI Readiness** stage covers the model side. A
  **Data Agent** stage after it would carry D1's surface and the 18 items.
- The Analyzer's readiness score becomes the entry condition for D1.
- D5 reuses the Enforcer's proven pattern: back up, preview a diff, verify by
  reading back, roll back on any failure.

## Risks

1. **Fabric auth is a real escalation.** Tenant, workspace, capacity, and a
   credential. D1–D2 deliberately avoid it so the module is useful before anyone
   sets that up.
2. **Data agents are in preview.** The surface has already moved once this
   month. Anything built on D3+ should expect churn and pin what it can.
3. **No local fixture.** The model side could be tested against copied folders;
   an agent cannot. D3+ needs a real dev-workspace agent to test against, or
   recorded API responses.
4. **The write path publishes.** A bad agent instruction reaches every consumer
   at once, with no per-user staging. Hence D5 last, and gated.

---

# Part 2 — Renaming to Modeling Studio

Mechanical, but it touches user-visible surfaces and one thing that will bite.

**Safe to rename now**
- Window title, header, and UI copy in `app/frontend/`
- `README.md`, `CLAUDE.md`, and the design docs
- `productName` in `app/electron-builder.yml`
- The docs-site title in `docs/`

**Needs care**
- `app/package.json` `name`, and the Python distribution name in
  `pyproject.toml` (`fabric-model-readiness`). Changing the Python package name
  **requires reinstalling the editable install** — and a stale editable install
  is precisely the failure that had the test suite broken. Rename it, reinstall
  in the same commit, and have `launch.bat`'s preflight catch the old name.
- `appId` in `electron-builder.yml` — changing it makes an installed build look
  like a different application. Only matters once something is packaged.
- The directory `app/fabric-model-readiness/` — renaming it invalidates every
  path in the editable install, `launch.bat`, and `.claude/launch.json`. This is
  the same class of change as the April move that quietly broke everything.

**Recommended split**
1. **Cosmetic first**: all user-visible strings and docs. Zero risk, immediate.
2. **Package names second**, with the reinstall in the same commit.
3. **Directory rename last, or never.** It buys tidiness and costs a repeat of a
   failure mode this repo has already suffered once. The Git remote
   (`fabric-model-readiness`) can stay as-is indefinitely — repository name and
   product name do not have to match.
