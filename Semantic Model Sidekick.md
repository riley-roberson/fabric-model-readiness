# Semantic Model Sidekick — Design Plan

## Context

Scout answers *"how good is this model?"* It cannot answer *"what should I be doing right now?"*

Today the linter throws all 64 checks at a model regardless of whether it is
day one or the day before UAT. On a half-built model that is not a report — it
is a pile of noise. Meanwhile the **Semantic Model Development Process** doc
defines an ordered path through a project, and the **Power BI Standards** doc
defines the rules, but neither is connected to the tool that can actually
measure compliance.

**Sidekick binds the three together**: the process supplies the spine, the
linter supplies objective truth, and a live assistant layer keeps track of where
you are and what is genuinely blocking you.

Source documents:
- `Semantic Model Development Process.docx` — 7 top-level phases, 10 stages, ~59 steps, 4 stakeholder gates
- `Power BI Standards.md` — the org rules the 17 `org_standards` checks derive from
- `BEAM Interview Outline.docx` — modelstorming method, story types, grain
- Templates: `TEMPLATE - BEAM Event Table.xlsx`, `TEMPLATE - Semantic Model *.pbit`, `TEMPLATE - Semantic Model UAT.xlsx`, `EDW Bus Matrix.xlsx`

---

## The two metaphors, made concrete

**LEGO instruction book** — the part people underrate about LEGO is not the
pictures, it is that the sequence is *finite, ordered, and unambiguous*. You
always know which step you are on, how many remain, and which pieces this step
needs. You cannot seat a brick wrong and be told three bags later.

| LEGO | Sidekick |
|---|---|
| Bag number | Stage (Bronze, Silver, Gold, PBI Dev, UAT…) |
| Numbered step | One process-doc action, "Step 23 of 59" |
| Parts callout box | Required inputs: BEAM table, bus matrix, `.pbit`, UAT sheet |
| The model growing on the page | Live star-schema diagram + readiness climbing |
| The satisfying click | Auto-verified evidence — the step proves *itself* done |

**Jarvis** — proactive, not interrogative. It already knows the state of the
build and volunteers what matters. It never asks you to tell it something it
could have looked up. The distinction that matters: a checklist app asks *"did
you create the star schema?"*; Sidekick **looks**, and tells you the grain is
wrong.

---

## Core concept: phase-aware linting

The single highest-value idea here. Every check gets an **earliest stage at
which it is meaningful**. Before that stage it is suppressed entirely — not
greyed out, *absent*, because a finding you cannot act on yet is noise.

| Stage | Checks that become live |
|---|---|
| **Gold / star schema** (3c) | `star_schema_structure`, `business_friendly_names`, `cross_table_disambiguation` |
| **PBI Development** (3d) | naming, `fact_table_hidden`, `surrogate_key_hidden`, `unnecessary_columns`, all descriptions, `data_categories`, `row_label_defined`, all relationship checks, all measure/DAX checks, `default_summarization`, `sort_by_column`, `incorrect_data_types`, `avoid_float_types`, display folders, `date_table_marked`, `synonyms`, `rls_*` |
| **AI Readiness** (new — see gap below) | all `ai_schema_*`, `noise_fields_excluded`, `hidden_field_conflicts`, all `verified_answer_*`, all `ai_instructions_*` |
| **UAT** (4) | performance and RLS checks re-run as gate conditions |

The score becomes **"82% of what should be true *at this stage*"** rather than a
demoralising 12.7 against a standard you were never meant to meet yet. The
absolute score stays available as a projection.

### A gap the process doc has

The process has **no Prep for AI / Data Agent step**. It ends PBI development at
"publish to testing workspace". All 20 AI-readiness checks have nowhere to
attach. Sidekick should propose a new stage between 3d and UAT, and this plan
assumes it — flagged explicitly so the doc owner can ratify or reject it rather
than have the tool quietly invent process.

---

## New rules the process doc implies

The process doc is a rules source the linter has never mined. These are **new
checks**, distinct from the 64:

| Check | Rule |
|---|---|
| `warehouse_layer_naming` | `zstage` prefix + schema = source system (`workday`, `virtuous`, `gapp`); `base` prefix + schema = business term; `fact`/`dim` prefix + schema = business term |
| `beam_coverage` | Every dimension and measure declared in the BEAM Event Table exists in the model |
| `bus_matrix_conformance` | Dimensions marked conformed in the EDW Bus Matrix are *reused*, not re-created per model |
| `template_provenance` | Model was created from the approved `.pbit`, not from scratch |
| `fact_story_type` | Fact table shape matches its declared BEAM story type — Discrete → transaction, Evolving → accumulating snapshot (multiple date FKs), Recurring → periodic snapshot (snapshot date + stated grain) |
| `scd_matches_requirements` | Historical/SCD handling matches what Requirements captured |

**How this works without a database connection:** PBIP partitions carry the
source M expressions, which contain the warehouse schema and table names. That
gives `warehouse_layer_naming` and much of `beam_coverage` entirely offline.
Requires extending the parser to read `partition` blocks — a live SQL connection
stays optional and later.

---

## Data model

```
Project
  ├─ id, name, root_path, model_path
  ├─ size: small | medium | large        → drives optional-step tailoring
  ├─ roles: {modeler, engineer, analyst, steward, stakeholder}
  ├─ business_event, story_type, grain   → from BEAM
  ├─ current_stage, started_at, target_date
  └─ Stage[10]
       └─ Step[~59]
            ├─ text, guidance, standards_refs[], template_refs[]
            ├─ optional_when: size == small, etc.
            ├─ evidence: Evidence
            └─ state: pending | in_progress | done | skipped(reason) | blocked
       └─ Gate?                          → 4 total, stakeholder attestation
```

### Evidence types — what makes a step "click"

| Type | Verified by | Example step |
|---|---|---|
| `manual` | User attestation + optional note | "Pray to start the meetings" |
| `artifact` | File exists at a known path/pattern | UAT sheet created from template |
| `lint` | Named Scout checks pass | "Turn off default aggregations" → `default_summarization` |
| `naming` | Warehouse object names match layer convention | "Prefix tables with `zstage`" |
| `derived` | Computed from the parsed model | "Create relationships" → `len(relationships) > 0` |
| `external` | Service/workspace state | "Publish to testing workspace" |

Roughly **half the ~59 steps are auto-verifiable**. That ratio is the whole
product: it is the difference between a checklist and an assistant.

---

## BEAM integration — the deepest hook

The BEAM Event Table is a *structured design artifact*. Parse the filled
template and you have a machine-readable target schema:

- W-questions (Who, What, When, Where, How Many, Why, How) → expected dimensions
- The declared grain → expected fact table grain
- Measures column, split stored-in-fact vs calculated-in-BI → expected measures
- Story type → expected fact table pattern

Then **diff the design against the built model**:

> Your BEAM table declares 6 dimensions. The model has 4.
> Missing: **Campaign**, **Channel**.
> Two measures are marked "calculated in BI layer" but exist as stored columns:
> `Total Donation`, `Gift Count`.

No other tool in this stack can say that, because no other tool has both sides.
This also drives `beam_coverage` and `fact_story_type`.

---

## The Jarvis layer

1. **Briefing on open** — 3–4 sentences, spoken register, always the same shape:
   where you are, what changed since last time, what blocks the next gate.
   > "Build → Semantic Model Development, step 4 of 8. Since Tuesday the model
   > gained 12 measures; 3 have no description and 2 use nested IF. Nothing
   > blocks you yet — the UAT gate needs RLS roles, which are step 7."

2. **Delta-only watch** — re-scan on file change; surface *new* stage-relevant
   findings only. Never re-report what you already saw. This is the difference
   between an assistant and an alarm.

3. **Ask anything** — natural language over project state + the three source
   documents. "Why do I need a row label?" answers from the Data Agent checklist
   *and* cites the standard. Grounded in retrieval over the docs, never invented.

4. **Do it for me** — auto-fixable findings hand off to the existing Enforcer
   (Power BI Modeling MCP, `ConnectFolder` → `Update` → `ExportToTmdlFolder`,
   backed up and diff-previewed). Sidekick decides *when* it is appropriate to
   offer; Enforcer does the writing.

5. **Proactive, bounded** — it volunteers, but only on stage-relevant, changed,
   actionable items. Everything else stays in the drawer.

---

## The LEGO layer (UI)

- **Spine**: vertical stepper, current stage expanded, others collapsed to a
  progress bar. Always visible: "Step 23 of 59 · Stage 4 of 10".
- **Step card**: the action, why it matters, standards citation, parts callout
  (templates/artifacts needed, one click to open), evidence state.
- **Parts callout**: literal LEGO-style box listing required inputs, each with
  present/missing state — templates resolve from the SharePoint process folder.
- **The build**: a star-schema diagram that grows as tables and relationships
  appear. This is the "model on the page" — it makes progress *felt*.
- **Gates**: full-width interstitials that cannot be passed while preconditions
  fail. Lists exactly what is outstanding. Records who signed off and when.
- **Score**: stage-adjusted percentage with a projected final, plus a burn-down
  of blocking findings per gate.

---

## Where it lives

**Desktop app (Electron + Python backend).** Non-negotiable for v1 — Sidekick
needs filesystem watching, warehouse/M parsing, MCP-driven enforcement, and
template access on SharePoint. The browser sandbox on the Vercel site can do
none of that.

A later trimmed web version could offer the process viewer plus manual checklist
(no auto-verification), reusing the manual-checklist pattern already built for
the docs site.

### Component layout

```
app/fabric-model-readiness/src/
  sidekick/
    process.py       # stages, steps, gates parsed from the process doc → data
    evidence.py      # the six evidence resolvers
    state.py         # project state, persistence, transitions
    briefing.py      # the Jarvis briefing generator
    beam.py          # BEAM Event Table parser + design-vs-model diff
    rules/
      warehouse.py   # warehouse_layer_naming, layer conventions
      design.py      # beam_coverage, bus_matrix_conformance, fact_story_type
  api/routes/
    sidekick.py      # GET state, POST advance, POST attest, SSE watch

app/frontend/src/
  sidekick/          # stepper, step card, parts callout, gate, schema diagram
```

`scout/rules/index.py` gains a `CHECK_STAGES` map — the phase-aware layer —
mirrored into TypeScript and guarded by the existing parity test.

### Persistence

`sidekick.json` at the **project root** (not inside `.SemanticModel`, since
bronze/silver/gold work is warehouse-side and outside the PBIP). Committable and
shareable, so a project's state travels with it. Gate attestations and step
transitions also append to Historian, which is already append-only.

---

## Build sequence

| Stage | Ships | Value on its own |
|---|---|---|
| **S1 — Spine** | Process doc encoded as data; stepper UI; manual evidence only; persistence | A real guided checklist matching org process |
| **S2 — Phase-aware linting** | `CHECK_STAGES` for all 64 checks; stage-adjusted score; suppression | Scout stops being noise on partial models |
| **S3 — Auto-evidence** | `lint`, `derived`, `artifact` resolvers; parts callout wired to templates | Half the steps verify themselves |
| **S4 — Gates** | 4 gates with preconditions + attestation → Historian | Process compliance becomes auditable |
| **S5 — Jarvis** | Briefing, delta watch, ask-anything over the three docs | It starts feeling like an assistant |
| **S6 — BEAM** | BEAM parser, design-vs-model diff, `beam_coverage`, `fact_story_type` | Catches design drift nothing else can see |
| **S7 — Warehouse** | Partition/M parsing, `warehouse_layer_naming` | Bronze/silver/gold steps verify themselves |
| **S8 — Do it for me** | Enforcer handoff from step cards | Closes the loop: find → explain → fix |

Each stage is independently useful. S1+S2 alone justify the feature.

---

## Risks and calls to make

1. **The process doc is not versioned as data.** Encoding ~59 steps by hand
   means the doc and the tool drift. Mitigation: keep the encoded process in one
   YAML file with a doc-revision stamp, and a test that flags when the source
   `.docx` changes.
2. **The AI Readiness stage does not exist in the process.** Sidekick would be
   inventing org process. Needs the doc owner's ratification — flagged, not
   assumed silently.
3. **"Highly variable" is the doc's own first sentence.** A rigid LEGO sequence
   fights that. Mitigation: steps are skippable *with a recorded reason*, and
   size (S/M/L) tailors which are expected. Gates stay hard.
4. **Warehouse verification without a DB connection** relies on M expressions in
   partitions being readable and honest. Fine for the naming checks; anything
   about row counts or data profiles needs a real connection.
5. **Template paths are SharePoint-synced** and user-specific. Needs a
   configurable root with graceful degradation when absent.
6. **Scope**: this is materially larger than the current linter. S1–S3 is the
   defensible MVP; S4–S8 should be re-evaluated after S3 lands.

---

## Verification

- **S1**: encoded process round-trips against the `.docx` — every `[[LI]]` under
  a heading becomes exactly one step; count assertion (59) catches drift.
- **S2**: parity test extended so `CHECK_STAGES` covers all 64 checks with no
  orphans, mirrored Python/TypeScript. A partial model scanned at Bronze stage
  reports zero findings; the same model at PBI Dev reports the expected set.
- **S3**: against a real project, each auto-evidence resolver agrees with manual
  judgement on a labelled sample.
- **S6**: BEAM diff on a project whose model is deliberately missing a dimension
  reports exactly that dimension.
- **End-to-end**: walk a copied real project from Launch to Closeout; every gate
  blocks correctly and every attestation lands in Historian.
