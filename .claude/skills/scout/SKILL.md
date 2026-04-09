---
name: scout
description: Read-only analyzer that scans Power BI semantic models (PBIP/PBIX) for Microsoft "Prep for AI" best practices and produces a structured findings report with a readiness score.
argument-hint: <path-to-model>
allowed-tools: Read, Grep, Glob, Bash
context: fork
agent: general-purpose
---

# Scout Agent -- Read-Only Semantic Model Analyzer

Follow all project rules in CLAUDE.md. You are the Scout agent.

**You are strictly read-only. You must NEVER write to or modify any model files.**

## Input

`$ARGUMENTS` is a path to either:
- A PBIP folder (e.g., `./MyModel.SemanticModel/`)
- A PBIX file (e.g., `./MyReport.pbix`)

Optionally include `--profile ai|org|both` to filter which checks run:
- **`ai`** -- Only Microsoft "Prep for AI" checks (descriptions, synonyms, AI schema, instructions, verified answers) plus shared checks (naming, star schema basics).
- **`org`** -- Only organizational standards checks from `Power BI Standards.md` (display folders, RLS, date tables, DAX patterns) plus shared checks.
- **`both`** (default) -- All checks. Equivalent to omitting the flag.

If given a PBIX file, extract it to `.scratch/extractions/` as a temp PBIP structure before analysis. Never modify the original PBIX.

## Steps

1. **Detect format**: Read `definition.pbism` to determine TMSL (version 1.0, uses `model.bim`) vs TMDL (version 4.0+, uses `definition/` folder).
2. **Parse model metadata**: Read all tables, columns, measures, relationships, and AI artifacts.
3. **Run all checks** from the categories below.
4. **Calculate readiness score** using the weighted scoring formula.
5. **Output a findings report** in the JSON format specified below.
6. **Write the report** to `findings/[model-name]/[scan-id].json` and update `findings/[model-name]/latest.json`.

## Standards Compliance

Before running checks, load `Power BI Standards.md` from the project root. This is the authoritative organizational standards document. When a finding matches a standard from that document, include the standard reference in the recommendation (e.g., "Per org standard: Data Modeling > Star Schemas"). If a Microsoft best practice conflicts with an organizational standard, defer to `Power BI Standards.md`.

## Best Practice Checks

### Schema Design

| Check | Severity | What to Look For |
|-------|----------|------------------|
| Star schema adherence | critical | Fact tables (events/transactions) with dimension tables (descriptive attributes). Flag flat/denormalized tables. |
| Table naming | high | Fact tables named after actions/events or prefixed `Fact`. Dimensions prefixed `Dim` or named as nouns. Flag `Table1`, `Sheet1`, `Query1`. |
| Column naming | high | Human-readable, unambiguous. Flag `Col1`, `CustNo`, `ProdID`, `Field1`. Expect `Customer Name`, `Product Category`. |
| Measure naming | high | Clearly reflects calculation purpose. Flag `M1`, `Calc1`, `Measure 1`. Expect `Total Sales`, `Average Customer Rating`. |
| Cross-table disambiguation | medium | Similarly named columns across tables must be distinguishable. Flag duplicate names like `Name` in both `Customer` and `Product`. |
| Wide table detection | medium | Flag tables with 30+ columns. Suggest unpivoting or normalizing. |
| Property bag detection | medium | Flag key-value pair patterns. Suggest dedicated columns. |

### Metadata Completeness

| Check | Severity | What to Look For |
|-------|----------|------------------|
| Table descriptions | critical | Every table must have a description. First 200 chars are used by Copilot. |
| Column descriptions | high | Every visible column should have a description (200-char effective limit). |
| Measure descriptions | critical | Every measure must have a description explaining what it calculates and when to use it. |
| Synonyms | medium | Key business columns should have synonyms for natural language matching. Check Properties > Synonyms and `Copilot/schema.json`. |
| Data categories | medium | Geography columns (`City`, `State`, `Country`, `Zip`) and date columns must have Data Category set. |

### Data Types and Aggregation

| Check | Severity | What to Look For |
|-------|----------|------------------|
| Correct data types | high | Monetary fields as Decimal, dates as Date, IDs as Whole Number. Flag dates stored as Text. |
| Default summarization | high | `Don't Summarize` on Year, Month, Day, ID, Age columns. `Average` on price/rate fields. Flag SUM on Year columns. |
| Sort By Column | low | Non-alphabetical fields (month names, day names) should have Sort By Column configured. |

### Relationships

| Check | Severity | What to Look For |
|-------|----------|------------------|
| Missing relationships | critical | Orphaned tables with no relationships. Copilot cannot traverse disconnected tables. |
| Inactive relationships | medium | Multiple relationship paths (role-playing dimensions). Suggest denormalization where possible. |
| Ambiguous paths | medium | Tables reachable by more than one active path. |
| Cardinality correctness | high | Many-to-many relationships should be flagged for review. |

### Measures and Calculations

| Check | Severity | What to Look For |
|-------|----------|------------------|
| Implicit measures | critical | Flag columns used for aggregation without explicit DAX measures. All calculations should be explicit DAX. |
| Time intelligence | medium | Check for TOTALYTD, SAMEPERIODLASTYEAR, or equivalent. Flag models with date tables but no time intelligence measures. |
| Duplicate/overlapping measures | high | Flag measures with similar names or identical DAX (`Total Sales` vs `Sales Amount` vs `Revenue`). |
| Helper measures exposed | medium | Intermediate calculation measures that should be hidden from end users and AI schema. |

### AI Preparation ("Prep for AI")

| Check | Severity | What to Look For |
|-------|----------|------------------|
| AI schema configured | critical | `Copilot/schema.json` exists and has field selections. Flag if missing entirely. |
| Noise fields excluded | high | Sort-helper columns, ID/key columns (relationship-only), and unused fields should be deselected in AI schema. |
| AI instructions present | high | `Copilot/Instructions/instructions.md` exists and is non-empty. |
| AI instructions quality | medium | Instructions should define business terms, time periods, metric preferences, default groupings. Flag generic/vague instructions. |
| Verified answers | medium | `Copilot/VerifiedAnswers/` should have at least a few verified answers for common questions. |
| Verified answer quality | low | Each verified answer should have 5-7 trigger phrases covering formal and conversational variations. |
| "Prepped for AI" flag | high | Model settings should have the AI preparation flag enabled. |
| Hidden field conflicts | medium | Verified answers must not reference hidden columns (they will fail silently). |

### Data Consistency

| Check | Severity | What to Look For |
|-------|----------|------------------|
| Inconsistent casing | medium | Column values with mixed casing (`Open`, `open`, `OPEN`). |
| Partitioned tables | low | Separate tables for different time ranges that should be unioned (`Sales2020`, `Sales2021`). |
| Multi-value columns | medium | Columns containing delimited lists that should be unpivoted into separate rows. |

## Output Format

Use the readiness score weights and rating thresholds defined in CLAUDE.md.

Write the findings report as JSON:

```json
{
  "scanId": "uuid",
  "modelPath": "./MyModel.SemanticModel/",
  "timestamp": "ISO-8601",
  "format": "TMDL",
  "summary": {
    "critical": 3,
    "high": 7,
    "medium": 12,
    "low": 4,
    "info": 2,
    "score": 62
  },
  "findings": [
    {
      "id": "f-001",
      "category": "metadata_completeness",
      "check": "table_descriptions",
      "severity": "critical",
      "object": "FactSales",
      "objectType": "table",
      "message": "Table 'FactSales' has no description. Copilot uses the first 200 characters of table descriptions to understand purpose.",
      "recommendation": "Add a description like: 'Transaction-level sales data capturing individual order line items with amount, quantity, and date.'",
      "autoFixable": true
    }
  ]
}
```

Review the Common Pitfalls section in CLAUDE.md before generating findings.
