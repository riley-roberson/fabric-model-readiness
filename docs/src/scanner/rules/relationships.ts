import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];

  // Build set of tables that participate in at least one relationship
  const connectedTables = new Set<string>();
  for (const rel of model.relationships) {
    connectedTables.add(rel.from_table);
    connectedTables.add(rel.to_table);
  }

  // Orphaned tables
  for (const table of model.tables) {
    if (!connectedTables.has(table.name) && !table.is_hidden) {
      findings.push(makeFinding({
        category: "relationships",
        check: "missing_relationships",
        severity: "critical",
        object: table.name,
        object_type: "table",
        message: `Table '${table.name}' has no relationships. Copilot cannot traverse disconnected tables.`,
      }));
    }
  }

  // Inactive relationships
  for (const rel of model.relationships) {
    if (!rel.is_active) {
      findings.push(makeFinding({
        category: "relationships",
        check: "inactive_relationships",
        severity: "medium",
        object: `${rel.from_table}.${rel.from_column} -> ${rel.to_table}.${rel.to_column}`,
        object_type: "relationship",
        message: `Inactive relationship between '${rel.from_table}' and '${rel.to_table}'. Consider denormalization if this is a role-playing dimension.`,
      }));
    }
  }

  // Many-to-many cardinality
  for (const rel of model.relationships) {
    const card = rel.cardinality.toLowerCase();
    if (card.includes("many") && card.replace("many", "").includes("many")) {
      findings.push(makeFinding({
        category: "relationships",
        check: "cardinality_correctness",
        severity: "high",
        object: `${rel.from_table} <-> ${rel.to_table}`,
        object_type: "relationship",
        message: `Many-to-many relationship between '${rel.from_table}' and '${rel.to_table}'. Review for correctness.`,
      }));
    }
  }

  // Bi-directional relationships
  for (const rel of model.relationships) {
    const direction = rel.cross_filter_direction.toLowerCase();
    if (direction === "bothdirections" || direction === "both") {
      findings.push(makeFinding({
        category: "relationships",
        check: "bidirectional_relationship",
        severity: "high",
        object: `${rel.from_table} <-> ${rel.to_table}`,
        object_type: "relationship",
        message: `Bi-directional relationship between '${rel.from_table}' and '${rel.to_table}'. Per org standard (Star Schemas): avoid bi-directional relationships. Use CROSSFILTER in DAX instead.`,
        recommendation: "Change to single-direction filtering and use CROSSFILTER() in DAX measures where needed.",
      }));
    }
  }

  // Ambiguous paths: tables reachable via more than one active relationship path
  const activeEdges: Record<string, string[]> = {};
  for (const rel of model.relationships) {
    if (rel.is_active) {
      (activeEdges[rel.from_table] ??= []).push(rel.to_table);
      (activeEdges[rel.to_table] ??= []).push(rel.from_table);
    }
  }

  for (const [tableName, neighbors] of Object.entries(activeEdges)) {
    if (neighbors.length !== new Set(neighbors).size) {
      findings.push(makeFinding({
        category: "relationships",
        check: "ambiguous_paths",
        severity: "medium",
        object: tableName,
        object_type: "table",
        message: `Table '${tableName}' has multiple active relationship paths to the same table.`,
      }));
    }
  }

  return findings;
}
