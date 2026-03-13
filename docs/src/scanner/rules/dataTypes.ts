import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

const NO_SUMMARIZE_KEYWORDS = ["year", "month", "day", "id", "age", "code", "number", "key"];
const NUMERIC_TYPES = ["int64", "double", "decimal", "whole number", "decimal number"];
const NAME_COL_PATTERN = /(month|day)\s*(name|label)/i;

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  for (const table of model.tables) {
    for (const col of table.columns) {
      const colLower = col.name.toLowerCase();

      // Default summarization: flag SUM on year/month/day/id/age columns
      const shouldNotSum = NO_SUMMARIZE_KEYWORDS.some((kw) => colLower.includes(kw));
      if (shouldNotSum && ["sum", ""].includes(col.summarize_by.toLowerCase())) {
        if (NUMERIC_TYPES.includes(col.data_type.toLowerCase())) {
          findings.push(makeFinding({
            category: "data_types",
            check: "default_summarization",
            severity: "high",
            object: `${table.name}.${col.name}`,
            object_type: "column",
            message: `Column '${col.name}' should use 'Don't Summarize' instead of SUM.`,
            auto_fixable: true,
          }));
        }
      }

      // Sort By Column for month/day name columns
      if (NAME_COL_PATTERN.test(colLower) && !col.sort_by_column) {
        findings.push(makeFinding({
          category: "data_types",
          check: "sort_by_column",
          severity: "low",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' appears to be a name field that needs Sort By Column configured for correct ordering.`,
          auto_fixable: true,
        }));
      }

      // Float data types
      if (["double", "single"].includes(col.data_type.toLowerCase())) {
        findings.push(makeFinding({
          category: "data_types",
          check: "avoid_float_types",
          severity: "medium",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' uses float type '${col.data_type}'. Per org standard (Data Modeling > General): avoid float data types unless necessary. Use Decimal Number instead.`,
          recommendation: "Change data type to Decimal (fixed decimal number) for financial/exact data.",
        }));
      }
    }
  }

  return findings;
}
