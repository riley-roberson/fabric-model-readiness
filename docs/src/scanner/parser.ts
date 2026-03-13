/**
 * Parses a PBIP .SemanticModel folder into the in-memory SemanticModel
 * representation using the File System Access API.
 *
 * Handles both TMSL (model.bim) and TMDL (definition/ folder) formats,
 * plus the Copilot/ subfolder.
 */

import type {
  ColumnInfo,
  CopilotConfig,
  MeasureInfo,
  ModelFormat,
  RelationshipInfo,
  RoleInfo,
  SemanticModel,
  TableInfo,
} from "./types";
import { emptyCopilotConfig } from "./types";

// ---------------------------------------------------------------------------
// File System Access API helpers
// ---------------------------------------------------------------------------

async function getSubDirectory(
  dir: FileSystemDirectoryHandle,
  name: string,
): Promise<FileSystemDirectoryHandle | null> {
  try {
    return await dir.getDirectoryHandle(name);
  } catch {
    return null;
  }
}

async function readTextFile(
  dir: FileSystemDirectoryHandle,
  name: string,
): Promise<string | null> {
  try {
    const fh = await dir.getFileHandle(name);
    const file = await fh.getFile();
    return await file.text();
  } catch {
    return null;
  }
}

async function listEntries(
  dir: FileSystemDirectoryHandle,
  extension?: string,
): Promise<{ name: string; kind: "file" | "directory" }[]> {
  const results: { name: string; kind: "file" | "directory" }[] = [];
  for await (const [name, handle] of dir.entries()) {
    if (extension && handle.kind === "file" && !name.endsWith(extension)) continue;
    results.push({ name, kind: handle.kind });
  }
  return results;
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function parse(dirHandle: FileSystemDirectoryHandle): Promise<SemanticModel> {
  const modelFormat = await detectFormat(dirHandle);
  const folderName = dirHandle.name;
  const modelName = folderName.endsWith(".SemanticModel")
    ? folderName.slice(0, -".SemanticModel".length)
    : folderName;

  if (modelFormat === "TMSL") {
    return parseTmsl(dirHandle, modelName);
  } else {
    return parseTmdl(dirHandle, modelName);
  }
}

// ---------------------------------------------------------------------------
// Format detection
// ---------------------------------------------------------------------------

async function detectFormat(dir: FileSystemDirectoryHandle): Promise<ModelFormat> {
  const pbism = await readTextFile(dir, "definition.pbism");
  if (pbism) {
    try {
      const content = JSON.parse(pbism);
      const version = content.version ?? "1.0";
      if (String(version).startsWith("4")) return "TMDL";
    } catch {
      // Fall through to heuristic
    }
  }
  // Heuristic: if definition/ folder exists, assume TMDL
  const defDir = await getSubDirectory(dir, "definition");
  if (defDir) return "TMDL";
  return "TMSL";
}

// ---------------------------------------------------------------------------
// TMSL parser (model.bim)
// ---------------------------------------------------------------------------

async function parseTmsl(dir: FileSystemDirectoryHandle, modelName: string): Promise<SemanticModel> {
  const bimText = await readTextFile(dir, "model.bim");
  if (!bimText) throw new Error("Expected model.bim in TMSL model folder");

  const bim = JSON.parse(bimText);
  const modelDef = bim.model ?? bim;
  const { tables, relationships, roles } = parseModelDef(modelDef);
  const copilot = await parseCopilotFolder(dir);

  return {
    name: modelName,
    path: modelName,
    format: "TMSL",
    tables,
    relationships,
    roles,
    copilot,
  };
}

function parseModelDef(modelDef: Record<string, unknown>): {
  tables: TableInfo[];
  relationships: RelationshipInfo[];
  roles: RoleInfo[];
} {
  const rawTables = (modelDef.tables ?? []) as Record<string, unknown>[];
  const tables: TableInfo[] = rawTables.map((t) => {
    // Detect date table via annotations
    let isDateTable = false;
    const annotations = (t.annotations ?? []) as Record<string, unknown>[];
    for (const ann of annotations) {
      if (ann.name === "__PBI_TimeIntelligenceEnabled") {
        isDateTable = String(ann.value ?? "").toLowerCase() === "true";
      }
    }

    const columns: ColumnInfo[] = ((t.columns ?? []) as Record<string, unknown>[]).map((c) => ({
      name: String(c.name ?? ""),
      table: String(t.name ?? ""),
      data_type: String(c.dataType ?? ""),
      description: String(c.description ?? ""),
      is_hidden: Boolean(c.isHidden ?? false),
      synonyms: [] as string[],
      data_category: String(c.dataCategory ?? ""),
      summarize_by: String(c.summarizeBy ?? ""),
      sort_by_column: String(c.sortByColumn ?? ""),
      display_folder: String(c.displayFolder ?? ""),
    }));

    const measures: MeasureInfo[] = ((t.measures ?? []) as Record<string, unknown>[]).map((m) => ({
      name: String(m.name ?? ""),
      table: String(t.name ?? ""),
      expression: normalizeExpression(m.expression),
      description: String(m.description ?? ""),
      is_hidden: Boolean(m.isHidden ?? false),
      display_folder: String(m.displayFolder ?? ""),
    }));

    return {
      name: String(t.name ?? ""),
      description: String(t.description ?? ""),
      columns,
      measures,
      is_hidden: Boolean(t.isHidden ?? false),
      is_date_table: isDateTable,
    };
  });

  const rawRels = (modelDef.relationships ?? []) as Record<string, unknown>[];
  const relationships: RelationshipInfo[] = rawRels.map((r) => ({
    from_table: String(r.fromTable ?? ""),
    from_column: String(r.fromColumn ?? ""),
    to_table: String(r.toTable ?? ""),
    to_column: String(r.toColumn ?? ""),
    is_active: r.isActive !== false,
    cardinality: `${r.fromCardinality ?? ""}:${r.toCardinality ?? ""}`,
    cross_filter_direction: String(r.crossFilteringBehavior ?? ""),
  }));

  const rawRoles = (modelDef.roles ?? []) as Record<string, unknown>[];
  const roles: RoleInfo[] = rawRoles.map((role) => {
    const filterExprs: string[] = [];
    for (const tp of (role.tablePermissions ?? []) as Record<string, unknown>[]) {
      const expr = String(tp.filterExpression ?? "");
      if (expr) filterExprs.push(expr);
    }
    return { name: String(role.name ?? ""), filter_expressions: filterExprs };
  });

  return { tables, relationships, roles };
}

// ---------------------------------------------------------------------------
// TMDL parser (definition/ folder)
// ---------------------------------------------------------------------------

async function parseTmdl(dir: FileSystemDirectoryHandle, modelName: string): Promise<SemanticModel> {
  const defDir = await getSubDirectory(dir, "definition");
  if (!defDir) {
    const copilot = await parseCopilotFolder(dir);
    return { name: modelName, path: modelName, format: "TMDL", tables: [], relationships: [], roles: [], copilot };
  }

  const model = await parseTmdlFolder(defDir, modelName);
  model.copilot = await parseCopilotFolder(dir);
  return model;
}

async function parseTmdlFolder(
  modelDir: FileSystemDirectoryHandle,
  modelName: string,
): Promise<SemanticModel> {
  const tables: TableInfo[] = [];
  const relationships: RelationshipInfo[] = [];
  const roles: RoleInfo[] = [];

  // Parse relationships
  const relText = await readTextFile(modelDir, "relationships.tmdl");
  if (relText) {
    relationships.push(...parseTmdlRelationships(relText));
  }

  // Parse roles
  const rolesDir = await getSubDirectory(modelDir, "roles");
  if (rolesDir) {
    const roleEntries = await listEntries(rolesDir, ".tmdl");
    for (const entry of roleEntries) {
      const text = await readTextFile(rolesDir, entry.name);
      if (text) {
        const role = parseTmdlRole(text);
        if (role) roles.push(role);
      }
    }
  }

  // Parse tables
  const tablesDir = await getSubDirectory(modelDir, "tables");
  if (tablesDir) {
    const tableEntries = await listEntries(tablesDir, ".tmdl");
    for (const entry of tableEntries) {
      const text = await readTextFile(tablesDir, entry.name);
      if (text) {
        const table = parseTmdlTable(text);
        if (table) tables.push(table);
      }
    }
  }

  // Check model.tmdl for date table annotation
  const modelTmdl = await readTextFile(modelDir, "model.tmdl");
  if (modelTmdl && modelTmdl.includes("__PBI_TimeIntelligenceEnabled = 1")) {
    for (const t of tables) {
      const lower = t.name.toLowerCase();
      if (lower.includes("date") || lower.includes("calendar")) {
        t.is_date_table = true;
      }
    }
  }

  return {
    name: modelName,
    path: modelName,
    format: "TMDL",
    tables,
    relationships,
    roles,
    copilot: emptyCopilotConfig(),
  };
}

function parseTmdlTable(content: string): TableInfo | null {
  const lines = content.split("\n");
  if (!lines.length) return null;

  const tableName = extractTmdlName(lines[0], "table");
  if (!tableName) return null;

  const columns: ColumnInfo[] = [];
  const measures: MeasureInfo[] = [];
  let isHidden = false;
  let description = "";
  let isDateTable = false;

  let i = 1;
  while (i < lines.length) {
    const stripped = lines[i].trim();

    if (stripped === "isHidden") {
      isHidden = true;
    } else if (stripped.startsWith("description:")) {
      description = stripped.split(":").slice(1).join(":").trim().replace(/^['"]|['"]$/g, "");
    } else if (stripped.startsWith("column ")) {
      const [col, endI] = parseTmdlColumn(lines, i, tableName);
      if (col) columns.push(col);
      i = endI;
      continue;
    } else if (stripped.startsWith("measure ")) {
      const [measure, endI] = parseTmdlMeasure(lines, i, tableName);
      if (measure) measures.push(measure);
      i = endI;
      continue;
    } else if (stripped.includes("__PBI_TimeIntelligenceEnabled") && stripped.includes("= 1")) {
      isDateTable = true;
    }

    i += 1;
  }

  return { name: tableName, description, columns, measures, is_hidden: isHidden, is_date_table: isDateTable };
}

function parseTmdlColumn(
  lines: string[],
  start: number,
  tableName: string,
): [ColumnInfo | null, number] {
  const colName = extractTmdlName(lines[start].trim(), "column");
  if (!colName) return [null, start + 1];

  let dataType = "";
  let description = "";
  let isHidden = false;
  let summarizeBy = "";
  let sortByColumn = "";
  let displayFolder = "";
  let dataCategory = "";

  const indent = getIndent(lines[start]);
  let i = start + 1;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const curIndent = getIndent(line);
    if (curIndent <= indent && line.trim()) break;

    const s = line.trim();
    if (s.startsWith("dataType:")) dataType = s.split(":").slice(1).join(":").trim();
    else if (s.startsWith("description:")) description = s.split(":").slice(1).join(":").trim().replace(/^['"]|['"]$/g, "");
    else if (s === "isHidden") isHidden = true;
    else if (s.startsWith("summarizeBy:")) summarizeBy = s.split(":").slice(1).join(":").trim();
    else if (s.startsWith("sortByColumn:")) sortByColumn = s.split(":").slice(1).join(":").trim();
    else if (s.startsWith("displayFolder:")) displayFolder = s.split(":").slice(1).join(":").trim();
    else if (s.startsWith("dataCategory:")) dataCategory = s.split(":").slice(1).join(":").trim();
    i++;
  }

  return [{
    name: colName,
    table: tableName,
    data_type: dataType,
    description,
    is_hidden: isHidden,
    synonyms: [],
    summarize_by: summarizeBy,
    sort_by_column: sortByColumn,
    display_folder: displayFolder,
    data_category: dataCategory,
  }, i];
}

function parseTmdlMeasure(
  lines: string[],
  start: number,
  tableName: string,
): [MeasureInfo | null, number] {
  const stripped = lines[start].trim();
  const eqIdx = stripped.indexOf("=");
  if (eqIdx < 0) return [null, start + 1];

  const namePart = stripped.slice(0, eqIdx).trim();
  const measureName = extractTmdlName(namePart, "measure");
  if (!measureName) return [null, start + 1];

  const expressionParts = [stripped.slice(eqIdx + 1).trim()];
  let description = "";
  let isHidden = false;
  let displayFolder = "";

  const indent = getIndent(lines[start]);
  let i = start + 1;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const curIndent = getIndent(line);
    if (curIndent <= indent && line.trim()) break;

    const s = line.trim();
    if (s.startsWith("description:")) {
      description = s.split(":").slice(1).join(":").trim().replace(/^['"]|['"]$/g, "");
    } else if (s === "isHidden") {
      isHidden = true;
    } else if (s.startsWith("displayFolder:")) {
      displayFolder = s.split(":").slice(1).join(":").trim();
    } else if (
      s.startsWith("formatString:") ||
      s.startsWith("annotation ") ||
      s.startsWith("changedProperty") ||
      s.startsWith("lineageTag")
    ) {
      // Skip known non-expression properties
    } else {
      expressionParts.push(s);
    }
    i++;
  }

  return [{
    name: measureName,
    table: tableName,
    expression: expressionParts.join("\n").trim(),
    description,
    is_hidden: isHidden,
    display_folder: displayFolder,
  }, i];
}

function parseTmdlRelationships(content: string): RelationshipInfo[] {
  const relationships: RelationshipInfo[] = [];
  const lines = content.split("\n");
  let i = 0;

  while (i < lines.length) {
    const stripped = lines[i].trim();
    if (stripped.startsWith("relationship ")) {
      let fromTable = "", fromCol = "", toTable = "", toCol = "";
      let isActive = true;
      let crossFilter = "";
      let cardinality = "";

      const indent = getIndent(lines[i]);
      i++;
      while (i < lines.length) {
        const line = lines[i];
        if (!line.trim()) { i++; continue; }
        const curIndent = getIndent(line);
        if (curIndent <= indent && line.trim()) break;

        const s = line.trim();
        if (s.startsWith("fromColumn:")) {
          [fromTable, fromCol] = splitTmdlColumnRef(s.split(":").slice(1).join(":").trim());
        } else if (s.startsWith("toColumn:")) {
          [toTable, toCol] = splitTmdlColumnRef(s.split(":").slice(1).join(":").trim());
        } else if (s.startsWith("isActive:")) {
          isActive = s.split(":")[1].trim().toLowerCase() !== "false";
        } else if (s.startsWith("crossFilteringBehavior:")) {
          crossFilter = s.split(":").slice(1).join(":").trim();
        } else if (s.startsWith("fromCardinality:") || s.startsWith("toCardinality:")) {
          cardinality += s.split(":").slice(1).join(":").trim() + ":";
        }
        i++;
      }

      if (fromTable && toTable) {
        relationships.push({
          from_table: fromTable,
          from_column: fromCol,
          to_table: toTable,
          to_column: toCol,
          is_active: isActive,
          cardinality: cardinality.replace(/:$/, ""),
          cross_filter_direction: crossFilter,
        });
      }
      continue;
    }
    i++;
  }

  return relationships;
}

function parseTmdlRole(content: string): RoleInfo | null {
  const lines = content.split("\n");
  if (!lines.length) return null;

  const roleName = extractTmdlName(lines[0].trim(), "role");
  if (!roleName) return null;

  const filters: string[] = [];
  for (const line of lines) {
    const s = line.trim();
    if (s.startsWith("filterExpression:")) {
      filters.push(s.split(":").slice(1).join(":").trim());
    }
  }

  return { name: roleName, filter_expressions: filters };
}

// ---------------------------------------------------------------------------
// Copilot folder parser
// ---------------------------------------------------------------------------

async function parseCopilotFolder(dir: FileSystemDirectoryHandle): Promise<CopilotConfig> {
  const config = emptyCopilotConfig();
  const copilotDir = await getSubDirectory(dir, "Copilot");
  if (!copilotDir) return config;

  // schema.json
  const schemaText = await readTextFile(copilotDir, "schema.json");
  if (schemaText) {
    config.schema_json_exists = true;
    try { config.schema_json = JSON.parse(schemaText); } catch { /* ignore parse errors */ }
  }

  // Instructions
  const instructionsDir = await getSubDirectory(copilotDir, "Instructions");
  if (instructionsDir) {
    const instrText = await readTextFile(instructionsDir, "instructions.md");
    if (instrText) {
      config.instructions_exist = true;
      config.instructions_content = instrText;
    }
  }

  // Verified answers
  const vaDir = await getSubDirectory(copilotDir, "VerifiedAnswers");
  if (vaDir) {
    const defsDir = await getSubDirectory(vaDir, "definitions");
    if (defsDir) {
      const entries = await listEntries(defsDir);
      for (const entry of entries) {
        if (entry.kind === "directory") {
          const answerDir = await getSubDirectory(defsDir, entry.name);
          if (answerDir) {
            const defnText = await readTextFile(answerDir, "definition.json");
            if (defnText) {
              try { config.verified_answers.push(JSON.parse(defnText)); } catch { /* ignore */ }
            }
          }
        }
      }
    }
  }

  // Settings
  const settingsText = await readTextFile(copilotDir, "settings.json");
  if (settingsText) {
    try { config.settings = JSON.parse(settingsText); } catch { /* ignore */ }
  }

  return config;
}

// ---------------------------------------------------------------------------
// TMDL helpers
// ---------------------------------------------------------------------------

function extractTmdlName(line: string, keyword: string): string {
  const prefix = keyword + " ";
  if (!line.startsWith(prefix)) return "";
  let rest = line.slice(prefix.length).trim();
  // For measures, strip the " = ..." part
  if (keyword === "measure") {
    const eqIdx = rest.indexOf(" = ");
    if (eqIdx >= 0) rest = rest.slice(0, eqIdx).trim();
  }
  if (rest.startsWith("'") && rest.endsWith("'")) return rest.slice(1, -1);
  return rest;
}

function splitTmdlColumnRef(ref: string): [string, string] {
  if (!ref.includes(".")) return [ref, ""];
  if (ref.startsWith("'")) {
    const endQuote = ref.indexOf("'", 1);
    const table = ref.slice(1, endQuote);
    const col = ref.slice(endQuote + 2); // skip '.
    return [table, col];
  }
  const dotIdx = ref.indexOf(".");
  return [ref.slice(0, dotIdx), ref.slice(dotIdx + 1)];
}

function getIndent(line: string): number {
  let count = 0;
  for (const ch of line) {
    if (ch === "\t") count++;
    else break;
  }
  return count;
}

function normalizeExpression(expr: unknown): string {
  if (Array.isArray(expr)) return expr.join("\n");
  return expr ? String(expr) : "";
}
