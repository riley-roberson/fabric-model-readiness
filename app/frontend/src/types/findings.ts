export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type Category =
  | "schema_design"
  | "metadata_completeness"
  | "data_types"
  | "relationships"
  | "measures"
  | "ai_preparation"
  | "data_consistency";

export type ObjectType =
  | "table"
  | "column"
  | "measure"
  | "relationship"
  | "copilot_schema"
  | "copilot_instructions"
  | "verified_answer"
  | "model";

export type Disposition = "accepted" | "rejected" | "deferred";

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

export const SEVERITY_ORDER: Severity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

export const SEVERITY_COLORS: Record<Severity, string> = {
  critical: "bg-red-100 text-red-800 border-red-300",
  high: "bg-orange-100 text-orange-800 border-orange-300",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-300",
  low: "bg-blue-100 text-blue-800 border-blue-300",
  info: "bg-gray-100 text-gray-600 border-gray-300",
};

export const CATEGORY_LABELS: Record<Category, string> = {
  schema_design: "Schema Design",
  metadata_completeness: "Metadata",
  data_types: "Data Types",
  relationships: "Relationships",
  measures: "Measures",
  ai_preparation: "AI Preparation",
  data_consistency: "Data Consistency",
};
