/**
 * Prep for AI checks, derived from the Microsoft "Semantic Model Preparation
 * Checklist for Fabric Data Agent".
 *
 * Covers the three model-side sections of that checklist:
 *   - AI Data Schema   (Prep for AI > Simplify data schema)
 *   - Verified Answers (Prep for AI > Verified answers)
 *   - AI Instructions  (Prep for AI > Add AI instructions)
 *
 * Checklist items that cannot be observed in a .SemanticModel folder (portal
 * configuration, notebook runs, Data Agent setup, live testing) are carried in
 * src/checklist/manual.ts instead and are not scored.
 */

import type { Finding, SemanticModel, TableInfo } from "../types";
import { makeFinding } from "../types";

/** Column-name shapes that should stay out of the AI schema. */
const NOISE_SUFFIXES = /(^|[\s_])(id|ids|key|keys|sk|fk|guid|uid|idx|index|sort|sortorder|ordinal|rowversion|hash)$/i;
const NOISE_PREFIXES = /^(sk|fk|pk|idx)([\s_]|$)/i;

/** Names suggesting a helper or intermediate calculation, not a reportable metric. */
const HELPER_MEASURE = /^(_|tmp|temp|test|helper|aux|base|calc)|(\b(helper|temp|internal|scratch|do not use|dnu)\b)/i;

const DATE_COLUMN = /\b(date|datetime|timestamp)\b|date$/i;

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  checkAiDataSchema(model, findings);
  checkVerifiedAnswers(model, findings);
  checkAiInstructions(model, findings);

  return findings;
}

// ---------------------------------------------------------------------------
// AI Data Schema (Prep for AI > Simplify data schema)
// ---------------------------------------------------------------------------

function checkAiDataSchema(model: SemanticModel, findings: Finding[]): void {
  const copilot = model.copilot;

  if (!copilot.schema_json_exists) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_schema_configured",
      severity: "critical",
      object: "Copilot/schema.json",
      object_type: "copilot_schema",
      message: "AI data schema (Copilot/schema.json) is missing entirely. Data Agent uses the Prep for AI schema to decide which tables, columns, and measures it may query.",
      recommendation: "Open the model in Power BI Desktop and configure Prep for AI > Simplify data schema.",
    }));
    // Every remaining schema check reads the selection -- nothing to read.
    return;
  }

  const selection = extractSelection(copilot.schema_json);

  // "Select only relevant tables, columns, and measures (very important)"
  checkSchemaScope(model, selection, findings);

  // "Include all dependent objects for selected measures"
  checkSchemaDependencies(model, selection, findings);

  // "Exclude helper measures and intermediate calculation objects"
  checkSchemaHelperObjects(model, selection, findings);

  // "Exclude duplicate or overlapping measures"
  checkSchemaDuplicateMeasures(model, selection, findings);

  // Noise columns that should not be exposed at all
  checkNoiseFields(model, findings);

  // "Verify no fields needed for verified answers are hidden"
  if (copilot.verified_answers.length > 0 && model.tables.length > 0) {
    checkHiddenFieldConflicts(model, findings);
  }
}

/**
 * Flags a schema that selects nearly the whole model. Prep for AI is a
 * narrowing step; selecting everything defeats it and degrades answer quality.
 */
function checkSchemaScope(model: SemanticModel, sel: Selection, findings: Finding[]): void {
  let visibleTables = 0;
  let visibleFields = 0;
  for (const table of model.tables) {
    if (table.is_hidden) continue;
    visibleTables++;
    visibleFields += table.columns.filter((c) => !c.is_hidden).length;
    visibleFields += table.measures.filter((m) => !m.is_hidden).length;
  }
  if (visibleTables === 0 || visibleFields === 0) return;

  const selectedFields = sel.columns.qualified.size + sel.measures.size;
  if (selectedFields === 0) return;

  const ratio = selectedFields / visibleFields;
  if (ratio >= 0.9) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_schema_scope",
      severity: "high",
      object: "Copilot/schema.json",
      object_type: "copilot_schema",
      message: `AI data schema selects ${selectedFields} of ${visibleFields} visible fields (${Math.round(ratio * 100)}%). Prep for AI is meant to narrow the model to what the agent actually needs.`,
      recommendation: "Deselect tables, columns, and measures outside the agent's defined scope. Fewer, well-chosen fields produce more accurate answers.",
    }));
  }
}

/**
 * Every measure in the schema pulls in the columns and measures its DAX
 * references. If a dependency is in the model but not in the schema, the agent
 * can select the measure but cannot resolve it.
 */
function checkSchemaDependencies(model: SemanticModel, sel: Selection, findings: Finding[]): void {
  if (sel.measures.size === 0) return;

  const modelMeasures = new Map<string, { table: string; expression: string }>();
  const modelColumns = new Set<string>();
  for (const table of model.tables) {
    for (const m of table.measures) {
      modelMeasures.set(m.name, { table: table.name, expression: m.expression });
    }
    for (const c of table.columns) {
      modelColumns.add(`${table.name}.${c.name}`.toLowerCase());
    }
  }

  for (const measureName of sel.measures) {
    const measure = modelMeasures.get(measureName);
    if (!measure) continue;

    const refs = extractDaxRefs(measure.expression);
    const missing: string[] = [];

    for (const dep of refs.measures) {
      if (dep === measureName) continue;
      if (!modelMeasures.has(dep)) continue; // not a measure -- likely an unqualified column
      if (!sel.measures.has(dep)) missing.push(`[${dep}]`);
    }

    for (const dep of refs.columns) {
      if (!modelColumns.has(dep.toLowerCase())) continue; // reference we cannot resolve
      if (!hasColumn(sel, dep)) missing.push(dep);
    }

    if (missing.length > 0) {
      const unique = [...new Set(missing)];
      findings.push(makeFinding({
        category: "ai_preparation",
        check: "ai_schema_dependencies",
        severity: "high",
        object: `${measure.table}.${measureName}`,
        object_type: "measure",
        message: `Measure '${measureName}' is in the AI data schema but ${unique.length} object(s) it depends on are not: ${unique.slice(0, 4).join(", ")}${unique.length > 4 ? ", ..." : ""}.`,
        recommendation: "Add the dependent objects to the AI data schema. Semantic Link Labs get_measure_dependencies can enumerate these when there are many.",
      }));
    }
  }
}

/** Helper and intermediate measures should not be offered to the agent. */
function checkSchemaHelperObjects(model: SemanticModel, sel: Selection, findings: Finding[]): void {
  for (const table of model.tables) {
    for (const m of table.measures) {
      if (!sel.measures.has(m.name)) continue;
      if (!HELPER_MEASURE.test(m.name)) continue;
      findings.push(makeFinding({
        category: "ai_preparation",
        check: "ai_schema_helper_objects",
        severity: "medium",
        object: `${table.name}.${m.name}`,
        object_type: "measure",
        message: `Measure '${m.name}' looks like a helper or intermediate calculation but is included in the AI data schema.`,
        recommendation: "Remove intermediate calculations from the AI data schema. Keep only measures a business user would ask for by name.",
      }));
    }
  }
}

/** Two measures with the same normalized name force the agent to guess. */
function checkSchemaDuplicateMeasures(model: SemanticModel, sel: Selection, findings: Finding[]): void {
  const byNormalized = new Map<string, string[]>();
  for (const table of model.tables) {
    for (const m of table.measures) {
      if (!sel.measures.has(m.name)) continue;
      const key = m.name.toLowerCase().replace(/[^a-z0-9]/g, "");
      const arr = byNormalized.get(key);
      if (arr) arr.push(`${table.name}.${m.name}`);
      else byNormalized.set(key, [`${table.name}.${m.name}`]);
    }
  }

  for (const refs of byNormalized.values()) {
    if (refs.length < 2) continue;
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_schema_duplicate_measures",
      severity: "medium",
      object: refs[0],
      object_type: "measure",
      message: `Overlapping measures are all selected in the AI data schema: ${refs.join(", ")}. The agent has no basis to choose between them.`,
      recommendation: "Keep one measure in the schema, or rename them so their difference is explicit in the name and description.",
    }));
  }
}

function checkNoiseFields(model: SemanticModel, findings: Finding[]): void {
  for (const table of model.tables) {
    for (const col of table.columns) {
      if (col.is_hidden) continue;
      const name = col.name.trim();
      if (!NOISE_SUFFIXES.test(name) && !NOISE_PREFIXES.test(name)) continue;
      findings.push(makeFinding({
        category: "ai_preparation",
        check: "noise_fields_excluded",
        severity: "high",
        object: `${table.name}.${col.name}`,
        object_type: "column",
        message: `Column '${col.name}' looks like a key, index, or sort helper and should not be exposed to the agent.`,
        recommendation: "Hide the column so it is excluded from the AI data schema.",
        auto_fixable: true,
      }));
    }
  }
}

function checkHiddenFieldConflicts(model: SemanticModel, findings: Finding[]): void {
  const hiddenCols = new Set<string>();
  for (const table of model.tables) {
    for (const col of table.columns) {
      if (col.is_hidden) {
        hiddenCols.add(`${table.name}.${col.name}`);
        hiddenCols.add(col.name);
      }
    }
  }

  for (const va of model.copilot.verified_answers) {
    const vaId = verifiedAnswerId(va);
    const vaStr = JSON.stringify(va);
    for (const hidden of hiddenCols) {
      if (vaStr.includes(hidden)) {
        findings.push(makeFinding({
          category: "ai_preparation",
          check: "hidden_field_conflicts",
          severity: "medium",
          object: `VerifiedAnswer/${vaId}`,
          object_type: "verified_answer",
          message: `Verified answer '${vaId}' may reference hidden column '${hidden}'. Fields used by a verified answer must be visible or it fails silently.`,
          recommendation: "Unhide the column, or rebuild the verified answer using visible fields.",
        }));
        break;
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Verified Answers (Prep for AI > Verified answers)
// ---------------------------------------------------------------------------

function checkVerifiedAnswers(model: SemanticModel, findings: Finding[]): void {
  const answers = model.copilot.verified_answers;

  if (answers.length === 0) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "verified_answers",
      severity: "medium",
      object: "Copilot/VerifiedAnswers/",
      object_type: "verified_answer",
      message: "No verified answers found. Verified answers pin the most common business questions to a known-correct visual.",
      recommendation: "Collect the questions your team asks most often and create a verified answer for each.",
    }));
    return;
  }

  for (const va of answers) {
    const vaId = verifiedAnswerId(va);
    const triggers = extractTriggers(va);

    // "Use 5-7 complete, robust trigger questions per verified answer"
    if (triggers.length < 5) {
      findings.push(makeFinding({
        category: "ai_preparation",
        check: "verified_answer_quality",
        severity: "low",
        object: `VerifiedAnswer/${vaId}`,
        object_type: "verified_answer",
        message: `Verified answer '${vaId}' has ${triggers.length} trigger question(s). Aim for 5-7 so both exact and semantic matching have enough to work with.`,
        recommendation: "Add trigger questions covering the different ways people ask this question.",
      }));
    }

    // "not partial phrases" -- a trigger should be a whole question
    const partials = triggers.filter((t) => t.trim().split(/\s+/).length < 4);
    if (partials.length > 0) {
      findings.push(makeFinding({
        category: "ai_preparation",
        check: "verified_answer_phrasing",
        severity: "low",
        object: `VerifiedAnswer/${vaId}`,
        object_type: "verified_answer",
        message: `Verified answer '${vaId}' has ${partials.length} very short trigger phrase(s) (e.g. "${partials[0]}"). Trigger questions should be complete questions, not fragments.`,
        recommendation: 'Replace fragments with full questions, and include both formal and conversational phrasings ("What was Q3 revenue?" and "how did we do last quarter").',
      }));
    }

    // "Configure up to 3 filters for flexible slicing"
    if (countFilters(va) === 0) {
      findings.push(makeFinding({
        category: "ai_preparation",
        check: "verified_answer_filters",
        severity: "low",
        object: `VerifiedAnswer/${vaId}`,
        object_type: "verified_answer",
        message: `Verified answer '${vaId}' has no filters configured. Without them it can only answer the one exact question.`,
        recommendation: "Add up to 3 filters (for example date range, region, product) so one verified answer covers a family of questions.",
      }));
    }
  }
}

// ---------------------------------------------------------------------------
// AI Instructions (Prep for AI > Add AI instructions)
// ---------------------------------------------------------------------------

interface InstructionRule {
  check: string;
  severity: "high" | "medium" | "low";
  pattern: RegExp;
  message: string;
  recommendation: string;
}

const INSTRUCTION_RULES: InstructionRule[] = [
  {
    check: "ai_instructions_terminology",
    severity: "medium",
    pattern: /\b(means?|stands for|refers to|terminolog|abbreviat|acronym|glossary|defined as|we (call|define))\b/i,
    message: "AI instructions do not define any business terminology. The agent cannot resolve org-specific terms it has never seen.",
    recommendation: 'Define your terms explicitly, e.g. "TMS is total media spend and should be calculated using the measure total_media_spend".',
  },
  {
    check: "ai_instructions_time_periods",
    severity: "medium",
    pattern: /\b(fiscal|ytd|mtd|qtd|year to date|month to date|quarter to date|peak season|calendar year|trailing|rolling)\b/i,
    message: "AI instructions do not define any time periods. Fiscal calendars and seasonal windows are not inferable from the model.",
    recommendation: 'State your fiscal year boundaries and any named periods, e.g. "our fiscal year starts July 1"; "peak season is November through December".',
  },
  {
    check: "ai_instructions_metric_preferences",
    severity: "medium",
    pattern: /\b(use the measure|use \[|prefer|should be calculated using|default measure|when (asked|someone asks)|always use)\b/i,
    message: "AI instructions do not state which measure to use for common questions. When several measures could answer a question, the agent guesses.",
    recommendation: 'Name the preferred measure per question type, e.g. "for revenue questions use [Net Revenue], not [Gross Revenue]".',
  },
  {
    check: "ai_instructions_groupings",
    severity: "low",
    pattern: /\b(group(ed)? by|default grouping|break ?down|slice by|by default,? (show|display|group)|analysis preference)\b/i,
    message: "AI instructions do not state default groupings or analysis preferences.",
    recommendation: 'Add the defaults you expect, e.g. "when no grouping is requested, break revenue down by product category".',
  },
  {
    check: "ai_instructions_dax_examples",
    severity: "low",
    pattern: /```|\bEVALUATE\b|\bSUMMARIZECOLUMNS\b|\bCALCULATE\s*\(/i,
    message: "AI instructions contain no example DAX. Complex scenarios are answered more reliably when the expected query pattern is shown.",
    recommendation: "Add one or two example DAX queries for your hardest recurring question shapes.",
  },
];

function checkAiInstructions(model: SemanticModel, findings: Finding[]): void {
  const copilot = model.copilot;
  const object = "Copilot/Instructions/instructions.md";

  if (!copilot.instructions_exist) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_instructions_present",
      severity: "high",
      object,
      object_type: "copilot_instructions",
      message: "AI instructions file is missing. This is where business terminology, time periods, and metric preferences are taught to the agent.",
      recommendation: "Add Prep for AI instructions covering terminology, fiscal periods, preferred measures, and ambiguous fields.",
      auto_fixable: true,
    }));
    return;
  }

  const content = copilot.instructions_content;
  const trimmed = content.trim();

  // "Keep instructions clear and specific (don't be too verbose)"
  if (trimmed.length < 200) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_instructions_conciseness",
      severity: "medium",
      object,
      object_type: "copilot_instructions",
      message: `AI instructions are only ${trimmed.length} characters. That is too thin to cover terminology, time periods, and metric preferences.`,
      recommendation: "Expand the instructions to cover your business terms, fiscal calendar, and which measure answers which question.",
      auto_fixable: true,
    }));
  } else if (trimmed.length > 8000) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_instructions_conciseness",
      severity: "medium",
      object,
      object_type: "copilot_instructions",
      message: `AI instructions are ${trimmed.length} characters. Verbose instructions slow responses and increase the chance of internal contradictions.`,
      recommendation: "Trim to the guidance that changes the agent's behavior. Move per-field context into object descriptions instead.",
    }));
  }

  for (const rule of INSTRUCTION_RULES) {
    if (rule.pattern.test(content)) continue;
    findings.push(makeFinding({
      category: "ai_preparation",
      check: rule.check,
      severity: rule.severity,
      object,
      object_type: "copilot_instructions",
      message: rule.message,
      recommendation: rule.recommendation,
    }));
  }

  checkAmbiguousDates(model, content, findings);
  checkAdvancedObjectGuidance(model, content, findings);
}

/**
 * A table carrying several date columns (Order Date / Ship Date / Due Date) is
 * ambiguous unless the instructions say which one to default to.
 */
function checkAmbiguousDates(model: SemanticModel, content: string, findings: Finding[]): void {
  const lower = content.toLowerCase();

  for (const table of model.tables) {
    if (table.is_hidden) continue;
    const dateCols = table.columns.filter(
      (c) => !c.is_hidden && (DATE_COLUMN.test(c.name) || /date|time/i.test(c.data_type)),
    );
    if (dateCols.length < 2) continue;

    const mentioned = dateCols.filter((c) => lower.includes(c.name.toLowerCase()));
    if (mentioned.length >= 2) continue;

    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_instructions_ambiguous_dates",
      severity: "high",
      object: table.name,
      object_type: "table",
      message: `Table '${table.name}' has ${dateCols.length} date columns (${dateCols.slice(0, 3).map((c) => c.name).join(", ")}${dateCols.length > 3 ? ", ..." : ""}) but the AI instructions do not disambiguate them.`,
      recommendation: 'State the default in the instructions, e.g. "date questions about orders use Order Date unless the user says shipped or due".',
    }));
  }
}

/**
 * Calculation groups, field parameters, and DAX UDFs do not behave like plain
 * measures. The checklist requires the instructions to explain how to use them.
 */
function checkAdvancedObjectGuidance(model: SemanticModel, content: string, findings: Finding[]): void {
  const lower = content.toLowerCase();
  const present: { label: string; tables: string[]; mentioned: boolean }[] = [];

  const calcGroups = model.tables.filter((t) => t.is_calculation_group);
  if (calcGroups.length > 0) {
    present.push({
      label: "calculation group",
      tables: calcGroups.map((t) => t.name),
      mentioned: lower.includes("calculation group") || lower.includes("calculation item"),
    });
  }

  const fieldParams = model.tables.filter((t) => t.is_field_parameter);
  if (fieldParams.length > 0) {
    present.push({
      label: "field parameter",
      tables: fieldParams.map((t) => t.name),
      mentioned: lower.includes("field parameter"),
    });
  }

  if (model.has_udfs) {
    present.push({
      label: "DAX user-defined function",
      tables: [],
      mentioned: lower.includes("user-defined function") || lower.includes("user defined function") || lower.includes("udf"),
    });
  }

  for (const item of present) {
    if (item.mentioned) continue;
    const where = item.tables.length > 0 ? ` (${item.tables.join(", ")})` : "";
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_instructions_advanced_objects",
      severity: "high",
      object: item.tables[0] ?? "Copilot/Instructions/instructions.md",
      object_type: item.tables.length > 0 ? "table" : "copilot_instructions",
      message: `Model uses ${item.label}s${where} but the AI instructions never explain how to use them. The agent will not apply them correctly on its own.`,
      recommendation: `Describe in the AI instructions when and how the agent should use each ${item.label}.`,
    }));
  }
}

// ---------------------------------------------------------------------------
// schema.json helpers
// ---------------------------------------------------------------------------

interface Selection {
  tables: Set<string>;
  columns: { qualified: Set<string>; bare: Set<string> };
  measures: Set<string>;
}

function emptySelection(): Selection {
  return {
    tables: new Set(),
    columns: { qualified: new Set(), bare: new Set() },
    measures: new Set(),
  };
}

function hasColumn(sel: Selection, qualified: string): boolean {
  if (sel.columns.qualified.has(qualified)) return true;
  const bare = qualified.slice(qualified.indexOf(".") + 1);
  return sel.columns.bare.has(bare);
}

/**
 * Walks Copilot/schema.json and collects the selected object names.
 *
 * The Prep for AI schema format is not contractual, so this reads it
 * structurally: any array under a "tables"/"columns"/"measures" key contributes
 * its entries' `name` values, at any nesting depth.
 */
function extractSelection(schemaJson: Record<string, unknown>): Selection {
  const sel = emptySelection();
  walkSchema(schemaJson, null, "", sel);
  return sel;
}

type SchemaKind = "table" | "column" | "measure" | null;

function walkSchema(node: unknown, kind: SchemaKind, tableCtx: string, sel: Selection): void {
  if (Array.isArray(node)) {
    for (const item of node) walkSchema(item, kind, tableCtx, sel);
    return;
  }
  if (node === null || typeof node !== "object") return;

  const obj = node as Record<string, unknown>;
  const name = typeof obj.name === "string" ? obj.name.trim() : "";
  let nextTable = tableCtx;

  if (name) {
    if (kind === "table") {
      sel.tables.add(name);
      nextTable = name;
    } else if (kind === "column") {
      sel.columns.qualified.add(tableCtx ? `${tableCtx}.${name}` : name);
      sel.columns.bare.add(name);
    } else if (kind === "measure") {
      sel.measures.add(name);
    }
  }

  for (const [key, value] of Object.entries(obj)) {
    const lower = key.toLowerCase();
    const childKind: SchemaKind =
      lower === "tables" || lower === "entities" ? "table"
      : lower === "columns" || lower === "fields" ? "column"
      : lower === "measures" ? "measure"
      : null;
    walkSchema(value, childKind, nextTable, sel);
  }
}

// ---------------------------------------------------------------------------
// Verified answer helpers (definition.json shape is not contractual)
// ---------------------------------------------------------------------------

function verifiedAnswerId(va: Record<string, unknown>): string {
  for (const key of ["name", "displayName", "id", "title"]) {
    const v = va[key];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "unknown";
}

function extractTriggers(va: Record<string, unknown>): string[] {
  for (const key of ["triggerPhrases", "trigger_phrases", "triggers", "questions", "utterances"]) {
    const v = va[key];
    if (Array.isArray(v)) {
      return v
        .map((t) => (typeof t === "string" ? t : typeof t === "object" && t !== null ? String((t as Record<string, unknown>).text ?? "") : ""))
        .filter((t) => t.trim().length > 0);
    }
  }
  return [];
}

function countFilters(va: Record<string, unknown>): number {
  for (const key of ["filters", "filterConfiguration", "filter_configuration"]) {
    const v = va[key];
    if (Array.isArray(v)) return v.length;
    if (v && typeof v === "object") return Object.keys(v).length;
  }
  return 0;
}

// ---------------------------------------------------------------------------
// DAX reference extraction
// ---------------------------------------------------------------------------

const QUALIFIED_COLUMN_REF = /'([^']+)'\[([^\]]+)\]|(?<![\w'])([A-Za-z_]\w*)\[([^\]]+)\]/g;
const BRACKET_REF = /\[([^\]]+)\]/g;

/**
 * Splits a DAX expression into the columns and measures it references.
 * Qualified column refs are consumed first so the remaining bracket refs are
 * unambiguously measure references.
 */
function extractDaxRefs(expression: string): { columns: string[]; measures: string[] } {
  const columns: string[] = [];
  const stripped = expression.replace(QUALIFIED_COLUMN_REF, (_match, t1, c1, t2, c2) => {
    columns.push(`${t1 ?? t2}.${c1 ?? c2}`);
    return " ";
  });

  const measures: string[] = [];
  for (const m of stripped.matchAll(BRACKET_REF)) {
    measures.push(m[1]);
  }

  return { columns, measures };
}

/** Exposed for the schema-design rules, which reuse the helper heuristic. */
export function isHelperMeasureName(name: string): boolean {
  return HELPER_MEASURE.test(name);
}

/** Exposed so other rule modules agree on what counts as a date column. */
export function dateColumnsOf(table: TableInfo) {
  return table.columns.filter((c) => DATE_COLUMN.test(c.name) || /date|time/i.test(c.data_type));
}
