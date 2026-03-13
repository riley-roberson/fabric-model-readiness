import type { Category, Finding, ScanSummary } from "./types";

const CATEGORY_WEIGHTS: Record<Category, number> = {
  ai_preparation: 0.20,
  metadata_completeness: 0.20,
  schema_design: 0.15,
  measures: 0.15,
  relationships: 0.10,
  data_types: 0.05,
  data_consistency: 0.05,
  org_standards: 0.10,
};

const CRITICAL_PENALTY_MULTIPLIER = 2;

export function computeSummary(
  findings: Finding[],
  totalChecksByCategory: Record<string, number>,
): ScanSummary {
  const summary: ScanSummary = { critical: 0, high: 0, medium: 0, low: 0, info: 0, score: 0 };

  // Count by severity
  for (const f of findings) {
    summary[f.severity] += 1;
  }

  // Weighted score
  const failuresByCat: Record<string, number> = {};
  for (const f of findings) {
    const penalty = f.severity === "critical" ? CRITICAL_PENALTY_MULTIPLIER : 1;
    failuresByCat[f.category] = (failuresByCat[f.category] ?? 0) + penalty;
  }

  let weightedScore = 0;
  let totalWeight = 0;

  for (const [cat, weight] of Object.entries(CATEGORY_WEIGHTS)) {
    const total = totalChecksByCategory[cat] ?? 0;
    if (total === 0) continue;
    const failed = failuresByCat[cat] ?? 0;
    const passing = Math.max(0, total - failed);
    const catScore = passing / total;
    weightedScore += catScore * weight;
    totalWeight += weight;
  }

  summary.score = totalWeight > 0 ? Math.round((weightedScore / totalWeight) * 1000) / 10 : 0;

  return summary;
}

export function rating(score: number): string {
  if (score >= 90) return "AI-Ready";
  if (score >= 75) return "Mostly Ready (minor gaps)";
  if (score >= 50) return "Needs Work (significant gaps)";
  return "Not Ready (fundamental issues)";
}

/**
 * Estimate total checks per category from findings.
 * Uses the heuristic that findings represent ~40% of total checks (pass rate ~60%).
 * This matches the Python CLI behavior.
 */
export function estimateTotalChecks(findings: Finding[]): Record<string, number> {
  const countByCat: Record<string, number> = {};
  for (const f of findings) {
    countByCat[f.category] = (countByCat[f.category] ?? 0) + 1;
  }

  const totals: Record<string, number> = {};
  for (const [cat, count] of Object.entries(countByCat)) {
    totals[cat] = Math.max(count, Math.ceil(count / 0.6));
  }

  // Ensure all categories are represented with at least 1 check
  for (const cat of Object.keys(CATEGORY_WEIGHTS)) {
    if (!(cat in totals)) {
      totals[cat] = 1;
    }
  }

  return totals;
}
