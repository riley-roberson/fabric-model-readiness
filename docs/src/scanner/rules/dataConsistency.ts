import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

const YEAR_SUFFIX = /^(.+?)(20\d{2})$/;

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  // Detect partitioned tables (Sales2020, Sales2021, etc.)
  const yearSuffixGroups: Record<string, string[]> = {};
  for (const table of model.tables) {
    const match = table.name.match(YEAR_SUFFIX);
    if (match) {
      const base = match[1];
      (yearSuffixGroups[base] ??= []).push(table.name);
    }
  }

  for (const [, tables] of Object.entries(yearSuffixGroups)) {
    if (tables.length > 1) {
      findings.push(makeFinding({
        category: "data_consistency",
        check: "partitioned_tables",
        severity: "low",
        object: tables[0],
        object_type: "table",
        message: `Tables ${[...tables].sort().join(", ")} appear to be year-partitioned. Consider unioning into a single table.`,
      }));
    }
  }

  return findings;
}
