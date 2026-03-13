import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  checkDisplayFolders(model, findings);
  checkRlsRoles(model, findings);
  checkDateTableMarked(model, findings);
  checkUseRelationship(model, findings);

  return findings;
}

function checkDisplayFolders(model: SemanticModel, findings: Finding[]): void {
  for (const table of model.tables) {
    if (table.is_hidden) continue;

    // Columns without display folders
    const visibleColsWithout = table.columns.filter((c) => !c.is_hidden && !c.display_folder);
    if (visibleColsWithout.length > 3) {
      findings.push(makeFinding({
        category: "org_standards",
        check: "column_display_folders",
        severity: "medium",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' has ${visibleColsWithout.length} visible columns without display folders. Per org standard (Data Modeling > Dimension Tables): group columns in display folders.`,
        recommendation: "Organize columns into logical display folders (e.g., 'Geography', 'Demographics').",
      }));
    }

    // Measures without display folders
    const visibleMeasuresWithout = table.measures.filter((m) => !m.is_hidden && !m.display_folder);
    if (visibleMeasuresWithout.length > 3) {
      findings.push(makeFinding({
        category: "org_standards",
        check: "measure_display_folders",
        severity: "medium",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' has ${visibleMeasuresWithout.length} measures without display folders. Per org standard (DAX): group measures in display folders.`,
        recommendation: "Organize measures into logical display folders (e.g., 'Sales Metrics', 'KPIs').",
      }));
    }
  }
}

function checkRlsRoles(model: SemanticModel, findings: Finding[]): void {
  const roleNames = new Set(model.roles.map((r) => r.name.toLowerCase()));

  if (model.roles.length === 0) {
    findings.push(makeFinding({
      category: "org_standards",
      check: "rls_roles_defined",
      severity: "high",
      object: "model",
      object_type: "model",
      message: "No RLS roles defined. Per org standard (Security and Sharing): define at least Admin and General roles.",
      recommendation: "Create an Admin role (no filters) and a General role (all filters applied).",
    }));
    return;
  }

  if (!roleNames.has("admin")) {
    findings.push(makeFinding({
      category: "org_standards",
      check: "rls_admin_role",
      severity: "high",
      object: "model",
      object_type: "model",
      message: "No 'Admin' RLS role found. Per org standard (Security and Sharing): the Admin role should have no filters.",
      recommendation: "Create an Admin role with no filter expressions.",
    }));
  }

  if (!roleNames.has("general")) {
    findings.push(makeFinding({
      category: "org_standards",
      check: "rls_general_role",
      severity: "high",
      object: "model",
      object_type: "model",
      message: "No 'General' RLS role found. Per org standard (Security and Sharing): the General role should have all filters applied.",
      recommendation: "Create a General role with appropriate row-level filters.",
    }));
  }
}

function checkDateTableMarked(model: SemanticModel, findings: Finding[]): void {
  for (const table of model.tables) {
    const tableLower = table.name.toLowerCase();
    if ((tableLower.includes("date") || tableLower.includes("calendar")) && !table.is_date_table) {
      findings.push(makeFinding({
        category: "org_standards",
        check: "date_table_marked",
        severity: "high",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' appears to be a date table but is not marked as one. Per org standard (Dates): mark calendar table as date table.`,
        recommendation: "Mark the table as a date table in Power BI (Table Tools > Mark as Date Table).",
      }));
    }
  }
}

function checkUseRelationship(model: SemanticModel, findings: Finding[]): void {
  // Detect duplicate dimension patterns
  const baseDims: Record<string, string[]> = {};
  for (const table of model.tables) {
    let base = table.name.replace(/^(dim|dimension)\s*/i, "");
    base = base.replace(/[_\s]?(order|ship|invoice|delivery|due|start|end|create|update|birth|hire).*$/i, "");
    const baseLower = base.toLowerCase().trim();
    if (baseLower) {
      (baseDims[baseLower] ??= []).push(table.name);
    }
  }

  for (const tables of Object.values(baseDims)) {
    if (tables.length > 1) {
      findings.push(makeFinding({
        category: "org_standards",
        check: "userelationship_preferred",
        severity: "medium",
        object: tables.join(", "),
        object_type: "table",
        message: `Tables ${tables.join(", ")} appear to be duplicated dimensions. Per org standard (Dimension Tables, Dates): use USERELATIONSHIP with inactive relationships instead of duplicating dimension tables.`,
        recommendation: "Consolidate into a single dimension table and use USERELATIONSHIP() in DAX measures for role-playing scenarios.",
      }));
    }
  }
}
