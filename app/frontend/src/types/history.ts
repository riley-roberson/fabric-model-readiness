/** Enriched history types returned by the API. */

export interface CategorySummary {
  accepted: number;
  deferred: number;
  rejected: number;
}

export interface AppliedSummary {
  totalAccepted: number;
  appliedViaMCP: number;
  skippedMCPUnsupported: number;
  deferred: number;
  rejected: number;
  notes?: string;
}

export interface SessionSummary {
  byCategory: Record<string, CategorySummary>;
  byAction: CategorySummary;
  appliedSummary: AppliedSummary | null;
}

export interface HistoryChange {
  findingId: string;
  category: string;
  object: string;
  action: "accepted" | "deferred" | "rejected";
  description: string;
  before: unknown;
  after: unknown;
  reason?: string | null;
}

export interface HistorySession {
  sessionId: string;
  scanId: string;
  timestamp: string;
  preScore: number;
  postScore: number | null;
  appliedTimestamp?: string;
  appliedSummary?: AppliedSummary;
  sessionSummary: SessionSummary;
  changes: HistoryChange[];
}

export interface DeferredItem {
  findingId: string;
  object: string;
  category: string;
  reason: string | null;
  description: string;
  sessionDate: string;
}

export interface EnrichedModelHistory {
  modelName: string;
  sessions: HistorySession[];
  deferredItems: DeferredItem[];
}

/** Category display config for the UI. */
export interface CategoryConfig {
  label: string;
  color: string;        // tailwind color name (blue, emerald, etc.)
  dotClass: string;     // bg-{color}-500
  textClass: string;    // text-{color}-400
  borderClass: string;  // border-{color}-500/30
  bgClass: string;      // bg-{color}-500/10
}

export const CATEGORY_CONFIGS: Record<string, CategoryConfig> = {
  schema_design:          { label: "Schema Design",     color: "blue",    dotClass: "bg-blue-500",    textClass: "text-blue-400",    borderClass: "border-blue-500/30",    bgClass: "bg-blue-500/10" },
  metadata_completeness:  { label: "Metadata",          color: "emerald", dotClass: "bg-emerald-500", textClass: "text-emerald-400", borderClass: "border-emerald-500/30", bgClass: "bg-emerald-500/10" },
  data_types_aggregation: { label: "Data Types",        color: "purple",  dotClass: "bg-purple-500",  textClass: "text-purple-400",  borderClass: "border-purple-500/30",  bgClass: "bg-purple-500/10" },
  measures_calculations:  { label: "Measures",          color: "orange",  dotClass: "bg-orange-500",  textClass: "text-orange-400",  borderClass: "border-orange-500/30",  bgClass: "bg-orange-500/10" },
  relationships:          { label: "Relationships",     color: "cyan",    dotClass: "bg-cyan-500",    textClass: "text-cyan-400",    borderClass: "border-cyan-500/30",    bgClass: "bg-cyan-500/10" },
  ai_preparation:         { label: "AI Preparation",    color: "amber",   dotClass: "bg-amber-500",   textClass: "text-amber-400",   borderClass: "border-amber-500/30",   bgClass: "bg-amber-500/10" },
  security:               { label: "Security",          color: "red",     dotClass: "bg-red-500",     textClass: "text-red-400",     borderClass: "border-red-500/30",     bgClass: "bg-red-500/10" },
  data_consistency:       { label: "Data Consistency",  color: "lime",    dotClass: "bg-lime-500",    textClass: "text-lime-400",    borderClass: "border-lime-500/30",    bgClass: "bg-lime-500/10" },
};

/** Ordered list of categories for display. */
export const CATEGORY_ORDER = [
  "schema_design",
  "metadata_completeness",
  "measures_calculations",
  "relationships",
  "data_types_aggregation",
  "ai_preparation",
  "security",
  "data_consistency",
];

export function getCategoryConfig(category: string): CategoryConfig {
  return CATEGORY_CONFIGS[category] ?? {
    label: category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    color: "slate",
    dotClass: "bg-slate-500",
    textClass: "text-slate-400",
    borderClass: "border-slate-500/30",
    bgClass: "bg-slate-500/10",
  };
}
