// ---------------------------------------------------------------------------
// Enums (string unions)
// ---------------------------------------------------------------------------

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

export type Category =
  | "schema_design"
  | "metadata_completeness"
  | "data_types"
  | "relationships"
  | "measures"
  | "ai_preparation"
  | "data_consistency"
  | "org_standards";

export type ModelFormat = "TMSL" | "TMDL";

export type ObjectType =
  | "table"
  | "column"
  | "measure"
  | "relationship"
  | "copilot_schema"
  | "copilot_instructions"
  | "verified_answer"
  | "model";

// ---------------------------------------------------------------------------
// Parsed semantic model
// ---------------------------------------------------------------------------

export interface ColumnInfo {
  name: string;
  table: string;
  data_type: string;
  description: string;
  is_hidden: boolean;
  synonyms: string[];
  data_category: string;
  summarize_by: string;
  sort_by_column: string;
  display_folder: string;
}

export interface MeasureInfo {
  name: string;
  table: string;
  expression: string;
  description: string;
  is_hidden: boolean;
  display_folder: string;
}

export interface RelationshipInfo {
  from_table: string;
  from_column: string;
  to_table: string;
  to_column: string;
  is_active: boolean;
  cardinality: string;
  cross_filter_direction: string;
}

export interface TableInfo {
  name: string;
  description: string;
  columns: ColumnInfo[];
  measures: MeasureInfo[];
  is_hidden: boolean;
  is_date_table: boolean;
}

export interface RoleInfo {
  name: string;
  filter_expressions: string[];
}

export interface CopilotConfig {
  schema_json_exists: boolean;
  schema_json: Record<string, unknown>;
  instructions_exist: boolean;
  instructions_content: string;
  verified_answers: Record<string, unknown>[];
  settings: Record<string, unknown>;
}

export interface SemanticModel {
  name: string;
  path: string;
  format: ModelFormat;
  tables: TableInfo[];
  relationships: RelationshipInfo[];
  roles: RoleInfo[];
  copilot: CopilotConfig;
}

// ---------------------------------------------------------------------------
// Scout output models
// ---------------------------------------------------------------------------

export interface Finding {
  id: string;
  category: Category;
  check: string;
  severity: Severity;
  object: string;
  object_type: ObjectType;
  message: string;
  recommendation: string;
  auto_fixable: boolean;
}

export interface ScanSummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  score: number;
}

export interface ScanResult {
  scan_id: string;
  model_name: string;
  model_format: ModelFormat;
  score: number;
  rating: string;
  summary: ScanSummary;
  findings: Finding[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

let _counter = 0;

export function generateFindingId(): string {
  _counter += 1;
  return `f-${_counter.toString(36).padStart(4, "0")}`;
}

export function makeFinding(
  partial: Omit<Finding, "id" | "recommendation" | "auto_fixable"> &
    Partial<Pick<Finding, "recommendation" | "auto_fixable">>,
): Finding {
  return {
    id: generateFindingId(),
    recommendation: "",
    auto_fixable: false,
    ...partial,
  };
}

export function emptyCopilotConfig(): CopilotConfig {
  return {
    schema_json_exists: false,
    schema_json: {},
    instructions_exist: false,
    instructions_content: "",
    verified_answers: [],
    settings: {},
  };
}
