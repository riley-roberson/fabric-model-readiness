import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

const TIME_INTELLIGENCE_FUNCTIONS =
  /\b(TOTALYTD|TOTALQTD|TOTALMTD|SAMEPERIODLASTYEAR|DATEADD|DATESYTD|PARALLELPERIOD|PREVIOUSMONTH|PREVIOUSQUARTER|PREVIOUSYEAR)\b/i;

const UNQUALIFIED_COLUMN_REF = /(?<!')\[(?!@)[A-Za-z_]\w*\]/g;
const SHORTENED_CALCULATE = /\[[\w\s]+\]\s*\(/;
const NESTED_IF = /\bIF\s*\(.*\bIF\s*\(/is;
const IFERROR_USAGE = /\bIFERROR\s*\(/i;
const DIVISION_OPERATOR = /(?<!\w)\/(?!\*)/;
const DIRECT_MEASURE_REF = /^\s*\[[\w\s]+\]\s*$/;
const MEASURE_TABLE_PATTERN = /^(measures?|_measures?|metrics?)/i;

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  const allMeasures: { table: string; name: string; expression: string }[] = [];
  let hasDateTable = false;
  let hasTimeIntelligence = false;

  for (const table of model.tables) {
    const tableLower = table.name.toLowerCase();
    if (tableLower.includes("date") || tableLower.includes("calendar")) {
      hasDateTable = true;
    }

    for (const measure of table.measures) {
      allMeasures.push({ table: table.name, name: measure.name, expression: measure.expression });

      if (TIME_INTELLIGENCE_FUNCTIONS.test(measure.expression)) {
        hasTimeIntelligence = true;
      }

      // Helper measures that are visible
      if (!measure.is_hidden && measure.name.startsWith("_")) {
        findings.push(makeFinding({
          category: "measures",
          check: "helper_measures_exposed",
          severity: "medium",
          object: `${table.name}.${measure.name}`,
          object_type: "measure",
          message: `Measure '${measure.name}' starts with '_' suggesting it's a helper, but it is not hidden.`,
          auto_fixable: true,
        }));
      }
    }
  }

  // Date table but no time intelligence
  if (hasDateTable && !hasTimeIntelligence && allMeasures.length > 0) {
    findings.push(makeFinding({
      category: "measures",
      check: "time_intelligence",
      severity: "medium",
      object: "model",
      object_type: "model",
      message: "Model has a date table but no time intelligence measures (TOTALYTD, SAMEPERIODLASTYEAR, etc.).",
    }));
  }

  // Duplicate / overlapping measure names
  const nameMap: Record<string, string[]> = {};
  for (const { table, name } of allMeasures) {
    const normalized = name.toLowerCase().replace(/[^a-z0-9]/g, "");
    (nameMap[normalized] ??= []).push(`${table}.${name}`);
  }
  for (const refs of Object.values(nameMap)) {
    if (refs.length > 1) {
      findings.push(makeFinding({
        category: "measures",
        check: "duplicate_measures",
        severity: "high",
        object: refs[0],
        object_type: "measure",
        message: `Possibly duplicate measures: ${refs.join(", ")}.`,
      }));
    }
  }

  // Measures not in dedicated measure tables
  for (const table of model.tables) {
    if (table.measures.length > 0 && table.columns.length > 0 && !MEASURE_TABLE_PATTERN.test(table.name)) {
      findings.push(makeFinding({
        category: "measures",
        check: "measure_table_required",
        severity: "medium",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' contains both columns and measures. Per org standard (DAX): store all measures in dedicated measure tables.`,
        recommendation: "Move measures to a dedicated measure table (e.g., '_Measures').",
      }));
    }
  }

  // DAX pattern checks
  const measureNamesSet = new Set(allMeasures.map((m) => m.name));

  for (const { table, name, expression } of allMeasures) {
    const qualifiedName = `${table}.${name}`;

    // Direct reference measures
    if (DIRECT_MEASURE_REF.test(expression)) {
      findings.push(makeFinding({
        category: "measures",
        check: "direct_measure_reference",
        severity: "low",
        object: qualifiedName,
        object_type: "measure",
        message: `Measure '${name}' is a direct reference to another measure. Per org standard (DAX): measures should not be direct references of other measures.`,
        recommendation: "Use measure branching or redefine the calculation.",
      }));
    }

    if (expression.trim().length < 3) continue;

    // Unqualified column references
    const unqualifiedRefs = expression.match(UNQUALIFIED_COLUMN_REF);
    if (unqualifiedRefs) {
      const colRefs = unqualifiedRefs.filter((r) => !measureNamesSet.has(r.slice(1, -1)));
      if (colRefs.length > 0) {
        findings.push(makeFinding({
          category: "measures",
          check: "fully_qualified_columns",
          severity: "medium",
          object: qualifiedName,
          object_type: "measure",
          message: `Measure '${name}' contains unqualified column references: ${colRefs.slice(0, 3).join(", ")}. Per org standard (DAX): always use fully qualified column references ('Table'[Column]).`,
          recommendation: "Use 'TableName'[ColumnName] syntax for all column references.",
        }));
      }
    }

    // Shortened CALCULATE syntax
    if (SHORTENED_CALCULATE.test(expression)) {
      findings.push(makeFinding({
        category: "measures",
        check: "shortened_calculate",
        severity: "medium",
        object: qualifiedName,
        object_type: "measure",
        message: `Measure '${name}' uses shortened CALCULATE syntax. Per org standard (DAX): use CALCULATE([measure], filter) instead of [measure](filter).`,
        recommendation: "Replace [measure](filter) with CALCULATE([measure], filter).",
      }));
    }

    // IFERROR usage
    if (IFERROR_USAGE.test(expression)) {
      findings.push(makeFinding({
        category: "measures",
        check: "iferror_usage",
        severity: "low",
        object: qualifiedName,
        object_type: "measure",
        message: `Measure '${name}' uses IFERROR. Per org standard (DAX): avoid IFERROR as it masks errors and hurts performance.`,
        recommendation: "Handle specific error conditions explicitly instead of using IFERROR.",
      }));
    }

    // Nested IF statements
    if (NESTED_IF.test(expression)) {
      findings.push(makeFinding({
        category: "measures",
        check: "nested_if",
        severity: "low",
        object: qualifiedName,
        object_type: "measure",
        message: `Measure '${name}' uses nested IF statements. Per org standard (DAX): use SWITCH(TRUE(), ...) instead of nested IFs.`,
        recommendation: "Refactor nested IF statements to use SWITCH(TRUE(), condition1, result1, ...).",
      }));
    }

    // Division using / operator
    if (DIVISION_OPERATOR.test(expression) && !expression.toLowerCase().includes("divide")) {
      findings.push(makeFinding({
        category: "measures",
        check: "use_divide_function",
        severity: "low",
        object: qualifiedName,
        object_type: "measure",
        message: `Measure '${name}' uses the / operator for division. Per org standard (DAX): use the DIVIDE function for safe division.`,
        recommendation: "Replace a / b with DIVIDE(a, b) to handle divide-by-zero gracefully.",
      }));
    }
  }

  return findings;
}
