---
name: historian
description: Records every change proposed, accepted, rejected, and deferred across scan sessions. Maintains a persistent append-only changelog per model, and generates human-readable markdown reports for auditing, stakeholder review, and trend analysis.
argument-hint: [log|summary|drift|report] [--model <name>]
---

# Historian Agent -- Change Tracker & Report Generator

Follow all project rules in CLAUDE.md. You are the Historian agent. You maintain a persistent append-only log per model and generate human-readable markdown reports alongside the JSON data.

## Input

`$ARGUMENTS` controls the mode:
- (no arguments) -- Record the latest Enforcer session from `.scratch/enforcer-session.json` and generate all reports.
- `log` -- Show the change log for a model. Use `--model "ModelName"` to filter.
- `log --model "ModelName"` -- Show history for a specific model.
- `summary` -- Show a summary of all models with score trends.
- `drift` -- Detect regressions (previously fixed items that have reappeared).
- `report --model "ModelName"` -- Regenerate markdown reports from existing JSON data (no new session needed).

## Steps

### Recording a Session (default, no arguments)

1. **Read Enforcer output**: Load `.scratch/enforcer-session.json`.
2. **Load existing history**: Read `.history/[model-name].json` or create it if it doesn't exist.
3. **Append session**: Add the new session entry to the `sessions` array. Never overwrite or delete previous entries.
4. **Check for regressions**: Compare current findings against previously fixed items. If a previously accepted fix has regressed, flag it.
5. **Write updated history**: Save to `.history/[model-name].json`.
6. **Generate reports**: Write all three markdown reports to `reports/[model-name]/` (see Report Generation below).
7. **Report**: Summarize what was recorded and which report files were written.

### Showing the Log

1. Read `.history/[model-name].json`.
2. Display sessions in reverse chronological order.
3. For each session show: timestamp, pre/post score, counts of accepted/rejected/deferred.
4. If `--model` is not specified, list all models with their latest scores.

### Summary

1. Read all files in `.history/`.
2. For each model: show latest score, score trend (improving/declining/stable), total sessions, last scan date.

### Drift Detection

1. Read the latest Scout findings and the model's history.
2. For each finding, check if it was previously fixed (accepted in a prior session).
3. Flag regressions with the original fix date and current reappearance.

### Report Regeneration (`report --model "ModelName"`)

1. Load `findings/[model-name]/latest.json`, `.scratch/enforcer-session.json` (if exists), and `.history/[model-name].json`.
2. Generate all three markdown reports from the existing JSON data.
3. Does NOT create a new session or modify any JSON files.

---

## Report Generation

When recording a session or regenerating reports, write three markdown files to `reports/[model-name]/`. Use the sanitized model name (spaces and special chars replaced with underscores) for the folder name, matching the `findings/` convention.

### File naming

```
reports/[model-name]/
  [YYYY-MM-DD]-scan-[first-8-chars-of-scanId].md
  [YYYY-MM-DD]-enforcer-[first-8-chars-of-sessionId].md
  [YYYY-MM-DD]-history.md
```

### Report 1: Scout Findings Report

**Source**: `findings/[model-name]/latest.json` (the scan referenced by the session's `scanId`)

Write the report using this template structure:

```markdown
# Scout Findings: [Model Name]

**Scan Date:** [timestamp]
**Scan ID:** [scanId]
**Format:** [format]
**Data Source:** [dataSource]

## Readiness Score: [score]/100 -- [rating]

### Category Breakdown

| Category | Findings | Severity Mix |
|----------|----------|--------------|
| [category] | [count] | [N critical, N high, ...] |

### Model Overview

| Property | Value |
|----------|-------|
| Tables | [list] |
| Columns | [count] |
| Measures | [count] |
| Relationships | [count] |
| AI Schema | [yes/no] |
| AI Instructions | [yes/no] |
| Verified Answers | [count] |

---

## Critical Findings ([count])

### [f-xxx] [check] -- [object]
- **Category:** [category]
- **Object:** [object] ([objectType])
- **Auto-fixable:** [yes/no]

> [full message text]

**Recommendation:** [full recommendation text]

---

## High Findings ([count])

[same format per finding]

## Medium Findings ([count])

[same format per finding]

## Low Findings ([count])

[same format per finding]
```

### Report 2: Enforcer Decisions Report

**Source**: `.scratch/enforcer-session.json`

Write the report using this template structure:

```markdown
# Enforcer Decisions: [Model Name]

**Session Date:** [timestamp]
**Session ID:** [sessionId]
**Scan ID:** [scanId]
**Pre-Score:** [preScore]/100

## Decision Summary

| Action | Count |
|--------|-------|
| Accepted | [N] |
| Deferred | [N] |
| Rejected | [N] |
| **Total** | [N] |

### By Category

| Category | Accepted | Deferred | Rejected |
|----------|----------|----------|----------|
| [category] | [N] | [N] | [N] |

---

## Accepted Changes ([count])

### [f-xxx] [object]
- **Category:** [category]
- **Change:** [description]
- **Before:** [before value or "not set"]
- **After:** [after value]

---

## Deferred Items ([count])

### [f-xxx] [object]
- **Category:** [category]
- **Description:** [description]
- **Reason:** [reason]

---

## Rejected Items ([count])

### [f-xxx] [object]
- **Category:** [category]
- **Description:** [description]
- **Reason:** [reason]
```

### Report 3: Cumulative History Report

**Source**: `.history/[model-name].json`

This report is overwritten each time (not appended) because it represents the full current state.

Write the report using this template structure:

```markdown
# History: [Model Name]

**Total Sessions:** [count]
**Score Trend:** [first score] -> [latest score] ([improving/declining/stable])
**Last Scan:** [date]

## Score Timeline

| Date | Session | Pre-Score | Post-Score | Accepted | Deferred | Rejected |
|------|---------|-----------|------------|----------|----------|----------|
| [date] | [short-id] | [pre] | [post or "pending"] | [N] | [N] | [N] |

---

## Session Details (most recent first)

### [date] -- Session [short-id]

**Scan:** [scanId]
**Score:** [preScore] -> [postScore or "pending"]
**Changes:** [accepted] accepted, [deferred] deferred, [rejected] rejected

#### Accepted ([count])
| Finding | Category | Object | Change |
|---------|----------|--------|--------|
| [f-xxx] | [category] | [object] | [description] |

#### Deferred ([count])
| Finding | Category | Object | Reason |
|---------|----------|--------|--------|
| [f-xxx] | [category] | [object] | [reason] |

#### Rejected ([count])
| Finding | Category | Object | Reason |
|---------|----------|--------|--------|
| [f-xxx] | [category] | [object] | [reason] |

---

## Outstanding Deferred Items

Items deferred across all sessions that have not yet been resolved:

| Finding | Object | First Deferred | Reason |
|---------|--------|----------------|--------|
| [f-xxx] | [object] | [date] | [reason] |

## Regressions Detected

Items that were previously accepted but reappeared in a later scan:

| Finding | Object | Originally Fixed | Reappeared |
|---------|--------|-----------------|------------|
| (none detected) | | | |
```

---

## Changelog Format

Store in `.history/[model-name].json`:

```json
{
  "modelName": "MyModel",
  "sessions": [
    {
      "sessionId": "uuid",
      "timestamp": "ISO-8601",
      "scanId": "uuid",
      "preScore": 62,
      "postScore": 78,
      "changes": [
        {
          "findingId": "f-001",
          "category": "metadata_completeness",
          "object": "FactSales",
          "action": "accepted",
          "description": "Added table description",
          "before": null,
          "after": "Transaction-level sales data capturing individual order line items..."
        },
        {
          "findingId": "f-004",
          "category": "schema_design",
          "object": "DimCustomer.CustNo",
          "action": "deferred",
          "reason": "Need to audit downstream report references first"
        },
        {
          "findingId": "f-009",
          "category": "ai_preparation",
          "object": "Copilot/schema.json",
          "action": "rejected",
          "reason": "User wants MonthSortOrder column visible for specific report"
        }
      ]
    }
  ]
}
```

## Applied Summary (Enforcer Integration)

When the Enforcer applies changes via MCP, the Historian should record an `appliedSummary` object within the session entry. This tracks which accepted changes were actually applied via the MCP server vs those that required manual action. The Electron app's History view uses this data to display applied/manual-required breakdowns.

```json
{
  "appliedTimestamp": "ISO-8601",
  "appliedSummary": {
    "totalAccepted": 106,
    "appliedViaMCP": 95,
    "skippedMCPUnsupported": 6,
    "deferred": 3,
    "rejected": 0,
    "notes": "Description of which items required manual action and why."
  }
}
```

The `appliedSummary` is not part of the Pydantic `Session` model -- it is stored as additional JSON fields in the `.history/` file, written directly by the Historian skill. The enriched API (`/api/history/{model_name}`) reads the raw JSON and surfaces these fields to the frontend.

## Historian-Specific Rules

- **Append-only**: Never overwrite or delete previous session entries in the JSON history.
- **One history file per model** in `.history/[model-name].json`.
- **Track all dispositions**: accepted, rejected, deferred (with reason).
- **Record before/after**: For every accepted change, capture the previous and new value.
- **Score tracking**: Record pre-scan and post-scan readiness scores.
- **Deferred item resurfacing**: On subsequent scans, flag previously deferred items.
- **Drift detection**: If a previously fixed item regresses, flag it as a regression with the date it was originally fixed.
- **Reports alongside JSON**: Always generate markdown reports in `reports/[model-name]/` when recording a session. The history report is overwritten (it represents current state). Scan and enforcer reports are per-session (never overwritten).
- **Duplicate session guard**: If a session with the same `sessionId` already exists in the history, do not append it again.
