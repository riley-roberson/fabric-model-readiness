import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

const BAD_TABLE_NAMES = /^(Table\d+|Sheet\d+|Query\d+)$/i;
const BAD_COLUMN_NAMES = /^(Col\d+|Field\d+)$/i;
const BAD_MEASURE_NAMES = /^(M\d+|Calc\d+|Measure\s*\d+)$/i;
const WIDE_TABLE_THRESHOLD = 30;
const FACT_TABLE_PATTERN = /^(fact|fct)/i;
const SURROGATE_KEY_PATTERN = /(id|key|sk|fk)$/i;

/** A denormalized island: enough columns to be a real table, no relationships. */
const DENORMALIZED_COLUMN_THRESHOLD = 10;

/** Column headers that are data values -- the signature of a pivoted source. */
const PIVOTED_COLUMN = /^((19|20)\d{2}|q[1-4]|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)([\s_-]?((19|20)\d{2}|\d{1,2}))?$/i;
const PIVOTED_THRESHOLD = 3;

/**
 * Truncated tokens that read as technical shorthand rather than business
 * language. The checklist calls these out by example: TR_AMT, CustName.
 */
const ABBREVIATION_TOKENS = new Set([
  "cust", "qty", "amt", "nbr", "num", "desc", "addr", "txn", "trx", "mgr",
  "dept", "acct", "invc", "ord", "prod", "cat", "grp", "val", "pct", "tot",
  "emp", "vend", "whs", "loc", "seq", "flg", "ind", "src", "tgt", "curr",
  "prev", "yr", "mo", "wk", "lvl", "typ", "nm", "dt", "cd", "org", "chg",
]);

/** Technical and audit columns that carry no business meaning for an agent. */
const HOUSEKEEPING_COLUMN =
  /^(etl|dw|dwh|stg|staging|sys)[\s_]|[\s_](etl|batch|checksum|hash|rowversion|lineage)[\s_]?|^(created|modified|updated|inserted|loaded)[\s_]?(by|on|at|date|time|ts)?$|^(is[\s_]?(deleted|current)|valid[\s_]?(from|to)|effective[\s_]?(from|to)|source[\s_]?system|record[\s_]?source|load[\s_]?(date|time|id))$/i;

/**
 * Splits a name into word tokens across spaces, underscores, and camelCase
 * boundaries, so "TR_AMT" and "CustName" both decompose.
 */
function tokenize(name: string): string[] {
  return name
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .split(/[\s_\-.]+/)
    .filter(Boolean);
}

/** True when a token reads as shorthand: a known abbreviation or vowel-less. */
function isCrypticToken(token: string): boolean {
  const lower = token.toLowerCase();
  if (ABBREVIATION_TOKENS.has(lower)) return true;
  if (token.length >= 3 && token.length <= 6 && !/[aeiouy]/i.test(token)) return true;
  return false;
}

function crypticTokensIn(name: string): string[] {
  return tokenize(name).filter(isCrypticToken);
}

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  /** Tables already reported as pivoted, so they are not reported twice. */
  const pivotedTables = new Set<string>();

  for (const table of model.tables) {
    // Bad table names
    if (BAD_TABLE_NAMES.test(table.name)) {
      findings.push(makeFinding({
        category: "schema_design",
        check: "table_naming",
        severity: "high",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' uses a generic name. Rename to reflect its business purpose.`,
      }));
    }

    // Wide tables
    if (table.columns.length >= WIDE_TABLE_THRESHOLD) {
      findings.push(makeFinding({
        category: "schema_design",
        check: "wide_table_detection",
        severity: "medium",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' has ${table.columns.length} columns. Consider normalizing or unpivoting.`,
      }));
    }

    // Cryptic table names ("Use clear, business-friendly names")
    const tableCryptic = crypticTokensIn(table.name);
    if (tableCryptic.length > 0 && !table.is_hidden) {
      findings.push(makeFinding({
        category: "schema_design",
        check: "business_friendly_names",
        severity: "medium",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' uses shorthand (${tableCryptic.join(", ")}). Agents match on names, so spell them the way users say them.`,
        recommendation: "Rename to the full business term, e.g. 'Cust' becomes 'Customer'.",
      }));
    }

    // Bad column names
    for (const col of table.columns) {
      if (BAD_COLUMN_NAMES.test(col.name)) {
        findings.push(makeFinding({
          category: "schema_design",
          check: "column_naming",
          severity: "high",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' in '${table.name}' uses a generic name.`,
        }));
      }

      if (col.is_hidden) continue;

      const colCryptic = crypticTokensIn(col.name);
      if (colCryptic.length > 0) {
        findings.push(makeFinding({
          category: "schema_design",
          check: "business_friendly_names",
          severity: "medium",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' uses shorthand (${colCryptic.join(", ")}) rather than business language.`,
          recommendation: "Rename to the full business term, e.g. 'TR_AMT' becomes 'Transaction Amount'.",
        }));
      }

      // Housekeeping columns the agent has no use for
      if (HOUSEKEEPING_COLUMN.test(col.name)) {
        findings.push(makeFinding({
          category: "schema_design",
          check: "unnecessary_columns",
          severity: "medium",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' looks like an audit or ETL column. It adds noise to the AI schema without answering business questions.`,
          recommendation: "Remove the column from the model, or hide it so it stays out of the AI data schema.",
          auto_fixable: true,
        }));
      }
    }

    // Pivoted structures: data values used as column headers
    const pivoted = table.columns.filter((c) => PIVOTED_COLUMN.test(c.name.trim()));
    if (pivoted.length >= PIVOTED_THRESHOLD) {
      pivotedTables.add(table.name);
      findings.push(makeFinding({
        category: "schema_design",
        check: "star_schema_structure",
        severity: "high",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' has ${pivoted.length} columns named after data values (${pivoted.slice(0, 3).map((c) => c.name).join(", ")}...). This is a pivoted structure, which agents cannot aggregate over.`,
        recommendation: "Unpivot these columns into a single attribute column plus a value column.",
      }));
    }

    // Bad measure names
    for (const measure of table.measures) {
      if (BAD_MEASURE_NAMES.test(measure.name)) {
        findings.push(makeFinding({
          category: "schema_design",
          check: "measure_naming",
          severity: "high",
          object: `${table.name}.${measure.name}`,
          object_type: "measure",
          message: `Measure '${measure.name}' uses a generic name. Rename to reflect its calculation purpose.`,
        }));
      }

      const measureCryptic = crypticTokensIn(measure.name);
      if (measureCryptic.length > 0 && !measure.is_hidden) {
        findings.push(makeFinding({
          category: "schema_design",
          check: "business_friendly_names",
          severity: "medium",
          object: `${table.name}.${measure.name}`,
          object_type: "measure",
          message: `Measure '${measure.name}' uses shorthand (${measureCryptic.join(", ")}) rather than business language.`,
          recommendation: "Rename to the term users would say out loud.",
        }));
      }
    }
  }

  // Build set of many-side tables from relationships (likely fact tables)
  const manySideTables = new Set<string>();
  const relatedTables = new Set<string>();
  for (const rel of model.relationships) {
    manySideTables.add(rel.from_table);
    relatedTables.add(rel.from_table);
    relatedTables.add(rel.to_table);
  }

  // Flat / denormalized tables: substantial, visible, and joined to nothing
  for (const table of model.tables) {
    if (table.is_hidden || table.is_calculation_group || table.is_field_parameter) continue;
    if (relatedTables.has(table.name)) continue;
    if (pivotedTables.has(table.name)) continue;
    if (table.columns.length < DENORMALIZED_COLUMN_THRESHOLD) continue;

    findings.push(makeFinding({
      category: "schema_design",
      check: "star_schema_structure",
      severity: "high",
      object: table.name,
      object_type: "table",
      message: `Table '${table.name}' has ${table.columns.length} columns and no relationships. A flat, denormalized table gives the agent no fact/dimension structure to reason over.`,
      recommendation: "Split into a fact table plus conformed dimension tables and relate them in a star schema.",
    }));
  }

  for (const table of model.tables) {
    const isFact = FACT_TABLE_PATTERN.test(table.name) || manySideTables.has(table.name);

    // Fact tables should be hidden
    if (isFact && !table.is_hidden) {
      findings.push(makeFinding({
        category: "schema_design",
        check: "fact_table_hidden",
        severity: "high",
        object: table.name,
        object_type: "table",
        message: `Fact table '${table.name}' is not hidden. Per org standard (Data Modeling > Fact Tables): fact tables should be hidden from users.`,
        recommendation: "Hide the fact table. Expose only measures and degenerate dimensions.",
        auto_fixable: true,
      }));
    }

    // Surrogate keys should be hidden on dimension tables
    if (!isFact) {
      for (const col of table.columns) {
        if (SURROGATE_KEY_PATTERN.test(col.name) && !col.is_hidden) {
          findings.push(makeFinding({
            category: "schema_design",
            check: "surrogate_key_hidden",
            severity: "medium",
            object: `${table.name}.${col.name}`,
            object_type: "column",
            message: `Surrogate key '${col.name}' in dimension '${table.name}' is not hidden. Per org standard (Data Modeling > Dimension Tables): hide surrogate keys from users.`,
            recommendation: "Set isHidden=true on the surrogate key column.",
            auto_fixable: true,
          }));
        }
      }
    }
  }

  // Cross-table column name duplicates
  const colNames: Record<string, string[]> = {};
  for (const table of model.tables) {
    for (const col of table.columns) {
      (colNames[col.name] ??= []).push(table.name);
    }
  }
  for (const [name, tables] of Object.entries(colNames)) {
    if (tables.length > 1) {
      findings.push(makeFinding({
        category: "schema_design",
        check: "cross_table_disambiguation",
        severity: "medium",
        object: name,
        object_type: "column",
        message: `Column '${name}' appears in tables: ${tables.join(", ")}. Disambiguate to avoid Copilot confusion.`,
      }));
    }
  }

  return findings;
}
