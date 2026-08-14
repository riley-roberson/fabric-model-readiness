import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

const GEOGRAPHY_KEYWORDS = ["city", "state", "country", "zip", "postal", "region", "latitude", "longitude"];

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  checkRowLabels(model, findings);

  for (const table of model.tables) {
    // Table descriptions
    if (!table.description.trim()) {
      findings.push(makeFinding({
        category: "metadata_completeness",
        check: "table_descriptions",
        severity: "critical",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' has no description. Copilot uses the first 200 characters of table descriptions to understand purpose.`,
        auto_fixable: true,
      }));
    }

    for (const col of table.columns) {
      // Column descriptions
      if (!col.is_hidden && !col.description.trim()) {
        findings.push(makeFinding({
          category: "metadata_completeness",
          check: "column_descriptions",
          severity: "high",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' in '${table.name}' has no description.`,
          auto_fixable: true,
        }));
      }

      // Data categories for geography columns
      const colLower = col.name.toLowerCase();
      if (GEOGRAPHY_KEYWORDS.some((kw) => colLower.includes(kw)) && !col.data_category) {
        findings.push(makeFinding({
          category: "metadata_completeness",
          check: "data_categories",
          severity: "medium",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' looks like a geography field but has no Data Category set.`,
          auto_fixable: true,
        }));
      }

      // Synonyms
      if (!col.is_hidden && !col.synonyms.length) {
        findings.push(makeFinding({
          category: "metadata_completeness",
          check: "synonyms",
          severity: "medium",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' in '${table.name}' has no synonyms for natural language matching.`,
          auto_fixable: true,
        }));
      }
    }

    // Measure descriptions
    for (const measure of table.measures) {
      if (!measure.description.trim()) {
        findings.push(makeFinding({
          category: "metadata_completeness",
          check: "measure_descriptions",
          severity: "critical",
          object: `${table.name}.${measure.name}`,
          object_type: "measure",
          message: `Measure '${measure.name}' has no description explaining what it calculates.`,
          auto_fixable: true,
        }));
      }
    }
  }

  return findings;
}

/**
 * Row labels tell Q&A and Data Agent which column names a row. Without one,
 * "show me the top customers" has no obvious column to return.
 * The checklist calls this out especially for dimension tables.
 */
function checkRowLabels(model: SemanticModel, findings: Finding[]): void {
  // A dimension is a table something else points at. Tables on the many side are
  // facts, and disconnected tables are a structural problem already reported by
  // star_schema_structure -- neither should be asked for a row label.
  const oneSideTables = new Set(model.relationships.map((r) => r.to_table));
  const manySideTables = new Set(model.relationships.map((r) => r.from_table));

  for (const table of model.tables) {
    if (table.is_hidden || table.is_calculation_group || table.is_field_parameter) continue;
    if (!oneSideTables.has(table.name)) continue;
    if (manySideTables.has(table.name)) continue;
    if (table.columns.length < 2) continue;

    if (table.columns.some((c) => c.is_default_label)) continue;

    findings.push(makeFinding({
      category: "metadata_completeness",
      check: "row_label_defined",
      severity: "medium",
      object: table.name,
      object_type: "table",
      message: `Dimension table '${table.name}' has no row label defined. Data Agent has no designated column to identify a row by.`,
      recommendation: "In Power BI Desktop, set the row label to the column that names the entity (e.g. Customer Name on Customer).",
      auto_fixable: true,
    }));
  }
}
