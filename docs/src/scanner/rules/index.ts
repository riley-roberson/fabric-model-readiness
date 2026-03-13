import type { Finding, SemanticModel } from "../types";
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
