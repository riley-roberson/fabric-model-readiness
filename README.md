# Fabric Semantic Model AI Readiness

Analyses a Power BI semantic model against Microsoft's Fabric Data Agent
preparation checklist and this organisation's Power BI standards, then applies
the fixes it can make safely.

Two front ends share one rule set:

| | What it is | Where it runs |
|---|---|---|
| **Desktop app** (`app/`) | Electron shell + Python backend. Scans, and **writes fixes back to the model**. | Locally, with filesystem and MCP access |
| **Docs site** (`docs/`) | Vite + React, browser-only. Scans and reports; never writes. | Vercel |

Both implement the same **64 checks**. A parity test holds them to identical
behaviour — see [Rule parity](#rule-parity).

---

## Prerequisites

- **Node.js** 20+ (LTS) — `node --version`
- **Python** 3.12+ available as the `py` launcher on Windows — `py --version`
- **Power BI Desktop** — only to open models; not needed to scan or fix them

The tool binaries under `tools/` are **not in the repo** (they are gitignored and
large). Enforcement needs one of them:

- **Power BI Modeling MCP Server** — install the `analysis-services.powerbi-modeling-mcp`
  VS Code extension, then extract it to
  `tools/powerbi-modeling-mcp/extracted/extension/`. Point `MCP_SERVER_PATH` at
  the executable to keep it elsewhere.
- **pbi-tools** (optional) — only needed to scan `.pbix` files saved in the newer
  XPress9-compressed format. Saving as a `.pbip` project avoids it entirely.

---

## Desktop app

### Setup, once

```bash
py -m pip install -e app/fabric-model-readiness
```

This must be an **editable install pointed at `app/`**. A stale install from
before the folder moved will still import when run from `src/`, then fail
everywhere else — including the whole test suite. `launch.bat` checks for this.

### Running it

Double-click **`app/launch.bat`**. It verifies prerequisites, compiles the
Electron main process, starts Vite, and launches the app, which spawns the Python
backend itself on a free port. On exit it shuts down both.

If a prerequisite is missing it stops immediately and prints the command to fix
it, rather than failing later as an opaque backend error.

### What it does

1. **Scout** — read-only scan of a `.SemanticModel` folder (or `.pbix`),
   producing findings and a 0–100 readiness score.
2. **Enforcer** — turns accepted findings into property writes, applies them, and
   verifies them against disk.
3. **Historian** — append-only record of every decision.

### Applying changes

Apply **edits files in your `.SemanticModel` folder.** The sequence is:

```
backup → connect → update (in memory) → export → re-parse → verify
```

- A full copy of the model is taken first, into `app/fabric-model-readiness/.backups/`.
- The MCP reports success on updates made to an *in-memory* model, so the only
  evidence a change reached disk is reading the folder back. That re-parse is
  what the run is judged on.
- If any change fails to verify, **the entire run is rolled back** from the backup.
- `POST /api/apply/preview` shows exactly what would be written, changing nothing.

Not every finding can be fixed mechanically. Structural ones (`star_schema_structure`)
and judgement calls (`row_label_defined` where several columns could be the
label) are reported as unsupported with a reason, never silently skipped.

---

## Docs site

```bash
npm install --prefix docs
npm run dev --prefix docs      # http://localhost:5173
npm run build --prefix docs
```

Deployed on Vercel from `docs/` (`framework: vite`, SPA rewrite). Folder access
uses the File System Access API, so it needs a Chromium browser; Firefox and
Safari get a fallback message. Nothing is uploaded — parsing happens in the tab.

---

## Testing

```bash
cd app/fabric-model-readiness && py -m pytest -q
```

### Rule parity

Two implementations of the same 64 checks will drift unless something stops
them. `tests/parity/` does:

- **`test_check_profiles_match`** — pure Python, always runs. Compares the check
  registry against the TypeScript source. A check registered on one side only is
  worse than a missing one: profile filtering defaults unknown checks to `both`,
  so it leaks into profiles it was never meant for.
- **`test_findings_match_typescript`** — runs the TypeScript rules under Node
  (via esbuild) against the same parsed model and compares findings by check,
  object, severity, and object type. Skips cleanly without Node or `docs/node_modules`.

---

## Repository layout

```
app/
  electron/              Main process, preload, Python supervisor
  frontend/              React UI for the desktop app
  fabric-model-readiness/
    src/scout/           Parser, rules, scorer  (read-only)
    src/enforcer/        MCP client, backup, operations, executor  (writes)
    src/historian/       Append-only change log
    src/api/             FastAPI wrapper over all three
  launch.bat             The one-click launcher

docs/                    Vite + React scanner, deployed to Vercel
tools/                   Downloaded binaries (gitignored)

CLAUDE.md                     Project context and conventions
Power BI Standards.md         Authoritative org standards -- source of the org checks
Semantic Model Sidekick.md    Design plan for the guided-project feature
```

## Scan profiles

| Profile | Checks | Use |
|---|---|---|
| `ai` | 47 | Microsoft Fabric Data Agent readiness |
| `org` | 28 | This organisation's Power BI standards |
| `both` | 64 | Everything (default) |

Checks tagged `both` count toward either profile, so the profile totals overlap
rather than summing to 64. Category weights are re-normalised when a profile
drops a category entirely.

Where a Microsoft recommendation conflicts with **Power BI Standards.md**, the
org standard wins and the conflict is noted in the finding.
