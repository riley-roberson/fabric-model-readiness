import type { Finding, SemanticModel } from "../types";
import { makeFinding } from "../types";

const NOISE_PATTERNS = ["id", "key", "sk", "fk", "sort", "order", "idx"];

export function check(model: SemanticModel): Finding[] {
  const findings: Finding[] = [];
  const copilot = model.copilot;

  // AI schema exists
  if (!copilot.schema_json_exists) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_schema_configured",
      severity: "critical",
      object: "Copilot/schema.json",
      object_type: "copilot_schema",
      message: "AI schema (Copilot/schema.json) is missing entirely. Copilot needs this to know which fields to use.",
    }));
  }

  // AI instructions exist
  if (!copilot.instructions_exist) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_instructions_present",
      severity: "high",
      object: "Copilot/Instructions/instructions.md",
      object_type: "copilot_instructions",
      message: "AI instructions file is missing. Add business context, terminology, and metric preferences.",
      auto_fixable: true,
    }));
  } else if (copilot.instructions_content.trim().length < 50) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "ai_instructions_quality",
      severity: "medium",
      object: "Copilot/Instructions/instructions.md",
      object_type: "copilot_instructions",
      message: "AI instructions exist but are very short. Add business terms, time periods, metric preferences, and default groupings.",
      auto_fixable: true,
    }));
  }

  // Verified answers
  if (!copilot.verified_answers.length) {
    findings.push(makeFinding({
      category: "ai_preparation",
      check: "verified_answers",
      severity: "medium",
      object: "Copilot/VerifiedAnswers/",
      object_type: "verified_answer",
      message: "No verified answers found. Add at least a few verified answers for common business questions.",
    }));
  } else {
    for (const va of copilot.verified_answers) {
      const triggers = (va.triggerPhrases ?? va.trigger_phrases ?? []) as string[];
      const vaId = String(va.id ?? "unknown");
      if (triggers.length < 5) {
        findings.push(makeFinding({
          category: "ai_preparation",
          check: "verified_answer_quality",
          severity: "low",
          object: `VerifiedAnswer/${vaId}`,
          object_type: "verified_answer",
          message: `Verified answer '${vaId}' has only ${triggers.length} trigger phrases. Aim for 5-7 covering formal and conversational variations.`,
        }));
      }
    }
  }

  // Noise fields in AI schema
  if (copilot.schema_json_exists) {
    checkNoiseFields(model, findings);
  }

  // Hidden field conflicts with verified answers
  if (copilot.verified_answers.length > 0 && model.tables.length > 0) {
    checkHiddenFieldConflicts(model, copilot.verified_answers, findings);
  }

  return findings;
}

function checkNoiseFields(model: SemanticModel, findings: Finding[]): void {
  for (const table of model.tables) {
    for (const col of table.columns) {
      const colLower = col.name.toLowerCase().replace(/[ _]/g, "");
      const isNoise = NOISE_PATTERNS.some((p) => colLower.includes(p));
      if (isNoise && !col.is_hidden) {
        findings.push(makeFinding({
          category: "ai_preparation",
          check: "noise_fields_excluded",
          severity: "high",
          object: `${table.name}.${col.name}`,
          object_type: "column",
          message: `Column '${col.name}' looks like an ID/sort/key column and should be hidden from the AI schema.`,
          auto_fixable: true,
        }));
      }
    }
  }
}

function checkHiddenFieldConflicts(
  model: SemanticModel,
  verifiedAnswers: Record<string, unknown>[],
  findings: Finding[],
): void {
  const hiddenCols = new Set<string>();
  for (const table of model.tables) {
    for (const col of table.columns) {
      if (col.is_hidden) {
        hiddenCols.add(`${table.name}.${col.name}`);
        hiddenCols.add(col.name);
      }
    }
  }

  for (const va of verifiedAnswers) {
    const vaId = String(va.id ?? "unknown");
    const vaStr = JSON.stringify(va);
    for (const hidden of hiddenCols) {
      if (vaStr.includes(hidden)) {
        findings.push(makeFinding({
          category: "ai_preparation",
          check: "hidden_field_conflicts",
          severity: "medium",
          object: `VerifiedAnswer/${vaId}`,
          object_type: "verified_answer",
          message: `Verified answer '${vaId}' may reference hidden column '${hidden}'. This will fail silently.`,
        }));
        break;
      }
    }
  }
}
