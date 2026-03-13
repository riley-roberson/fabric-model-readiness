import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

const BAD_TABLE_NAMES = /^(Table\d+|Sheet\d+|Query\d+)$/i;
const BAD_COLUMN_NAMES = /^(Col\d+|Field\d+)$/i;
const BAD_MEASURE_NAMES = /^(M\d+|Calc\d+|Measure\s*\d+)$/i;
const WIDE_TABLE_THRESHOLD = 30;
const FACT_TABLE_PATTERN = /^(fact|fct)/i;
const SURROGATE_KEY_PATTERN = /(id|key|sk|fk)$/i;

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

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
    }
  }

  // Build set of many-side tables from relationships (likely fact tables)
  const manySideTables = new Set<string>();
  for (const rel of model.relationships) {
    manySideTables.add(rel.from_table);
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
