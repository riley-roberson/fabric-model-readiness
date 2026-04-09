import type { Finding, Profile, SemanticModel } from "../types";
import { check as checkSchemaDesign } from "./schemaDesign";
import { check as checkMetadata } from "./metadata";
import { check as checkRelationships } from "./relationships";
import { check as checkMeasures } from "./measures";
import { check as checkAiPrep } from "./aiPrep";
import { check as checkDataTypes } from "./dataTypes";
import { check as checkDataConsistency } from "./dataConsistency";
import { check as checkOrgStandards } from "./orgStandards";

export interface RuleModule {
  name: string;
  check: (model: SemanticModel) => Finding[];
}

const RULE_MODULES: RuleModule[] = [
  { name: "Schema Design", check: checkSchemaDesign },
  { name: "Metadata", check: checkMetadata },
  { name: "Relationships", check: checkRelationships },
  { name: "Measures", check: checkMeasures },
  { name: "AI Preparation", check: checkAiPrep },
  { name: "Data Types", check: checkDataTypes },
  { name: "Data Consistency", check: checkDataConsistency },
  { name: "Org Standards", check: checkOrgStandards },
];

// ---------------------------------------------------------------------------
// Check-to-profile mapping (mirrors Python CHECK_PROFILES in shared/config.py)
// ---------------------------------------------------------------------------

export const CHECK_PROFILES: Record<string, string> = {
  // Schema design
  table_naming: "both",
  column_naming: "both",
  measure_naming: "both",
  wide_table_detection: "both",
  fact_table_hidden: "both",
  surrogate_key_hidden: "both",
  cross_table_disambiguation: "ai",
  // Metadata completeness
  table_descriptions: "ai",
  column_descriptions: "ai",
  measure_descriptions: "ai",
  data_categories: "ai",
  synonyms: "ai",
  // Relationships
  missing_relationships: "ai",
  inactive_relationships: "both",
  cardinality_correctness: "both",
  bidirectional_relationship: "org",
  ambiguous_paths: "both",
  // Measures and calculations
  helper_measures_exposed: "ai",
  time_intelligence: "ai",
  duplicate_measures: "both",
  measure_table_required: "org",
  direct_measure_reference: "org",
  fully_qualified_columns: "org",
  shortened_calculate: "org",
  iferror_usage: "org",
  nested_if: "org",
  use_divide_function: "org",
  // AI preparation
  ai_schema_configured: "ai",
  ai_instructions_present: "ai",
  ai_instructions_quality: "ai",
  verified_answers: "ai",
  verified_answer_quality: "ai",
  noise_fields_excluded: "ai",
  hidden_field_conflicts: "ai",
  // Data types and aggregation
  default_summarization: "both",
  sort_by_column: "ai",
  avoid_float_types: "org",
  // Data consistency
  partitioned_tables: "org",
  // Organizational standards
  column_display_folders: "org",
  measure_display_folders: "org",
  rls_roles_defined: "org",
  rls_admin_role: "org",
  rls_general_role: "org",
  date_table_marked: "org",
  userelationship_preferred: "org",
};

/**
 * Filter findings to only those matching the active profile.
 * - "both": returns all findings unchanged.
 * - "ai": keeps checks tagged "ai" or "both".
 * - "org": keeps checks tagged "org" or "both".
 * Unknown checks default to "both" (always included).
 */
export function filterByProfile(findings: Finding[], profile: Profile): Finding[] {
  if (profile === "both") return findings;
  const allowed = profile === "ai" ? new Set(["ai", "both"]) : new Set(["org", "both"]);
  return findings.filter((f) => allowed.has(CHECK_PROFILES[f.check] ?? "both"));
}

// ---------------------------------------------------------------------------

export interface ScanProgress {
  current: number;
  total: number;
  module: string;
}

export function runAllChecks(
  model: SemanticModel,
  onProgress?: (progress: ScanProgress) => void,
): Finding[] {
  const allFindings: Finding[] = [];
  const total = RULE_MODULES.length;

  for (let i = 0; i < RULE_MODULES.length; i++) {
    const mod = RULE_MODULES[i];
    onProgress?.({ current: i + 1, total, module: mod.name });
    const findings = mod.check(model);
    allFindings.push(...findings);
  }

  return allFindings;
}
