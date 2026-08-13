/**
 * Items from the Microsoft "Semantic Model Preparation Checklist for Fabric
 * Data Agent" that cannot be observed in a .SemanticModel folder.
 *
 * These describe work in a Fabric notebook, the Power BI Desktop UI, the Data
 * Agent itself, or live testing. Scout cannot verify them, so they are tracked
 * as a manual checklist and deliberately excluded from the readiness score --
 * a model should not be penalized for work the scanner cannot see.
 *
 * Everything else in that checklist is implemented as a scanner rule; see
 * CHECK_PROFILES in ../scanner/rules/index.ts.
 */

export type ManualEmphasis = "important" | "warning";

export interface ManualItem {
  /** Stable id -- persisted to localStorage, so never renumber in place. */
  id: string;
  section: string;
  text: string;
  /** "important" mirrors the checklist's warning marker; "warning" mirrors its prohibition. */
  emphasis?: ManualEmphasis;
  /** Supporting Microsoft documentation, where the checklist links it. */
  docUrl?: string;
  docLabel?: string;
}

export const MANUAL_CHECKLIST_SOURCE =
  "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-semantic-model";

export const MANUAL_SECTIONS = [
  "Semantic Model Optimization",
  "AI Data Schema",
  "Verified Answers",
  "AI Instructions",
  "Data Agent Configuration",
  "Testing and Validation",
] as const;

export const MANUAL_ITEMS: ManualItem[] = [
  // -------------------------------------------------------------------------
  // Semantic Model Optimization
  // -------------------------------------------------------------------------
  {
    id: "opt-bpa",
    section: "Semantic Model Optimization",
    text: "Run Best Practice Analyzer in a Fabric notebook",
    docUrl: "https://learn.microsoft.com/en-us/power-bi/transform-model/service-notebooks",
    docLabel: "Best Practice Analyzer",
  },
  {
    id: "opt-memory-analyzer",
    section: "Semantic Model Optimization",
    text: "Run Semantic Model Memory Analyzer in a Fabric notebook",
    docUrl: "https://learn.microsoft.com/en-us/power-bi/transform-model/service-notebooks#model-memory-analyzer",
    docLabel: "Model Memory Analyzer",
  },
  {
    id: "opt-direct-lake",
    section: "Semantic Model Optimization",
    text: "If using a Direct Lake semantic model, perform Direct Lake specific optimizations such as V-Order",
    docUrl: "https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-understand-storage",
    docLabel: "Direct Lake storage guidance",
  },
  {
    id: "opt-performance-analyzer",
    section: "Semantic Model Optimization",
    text: "Use Performance Analyzer to test query performance on measures included in the AI data schema",
    docUrl: "https://learn.microsoft.com/en-us/power-bi/create-reports/performance-analyzer",
    docLabel: "Performance Analyzer",
  },
  {
    id: "opt-report-scoped-measures",
    section: "Semantic Model Optimization",
    text: "Move any report-scoped measures the Data Agent should use into the semantic model -- report-scoped measures are not accessible to the Data Agent",
  },

  // -------------------------------------------------------------------------
  // AI Data Schema
  // -------------------------------------------------------------------------
  {
    id: "schema-define-scope",
    section: "AI Data Schema",
    text: "Define the scope of your Data Agent: questions it should and should not answer, user personas, what is out of scope, security requirements",
  },
  {
    id: "schema-match-data-agent",
    section: "AI Data Schema",
    text: "Ensure the tables selected here match what you will select in the Data Agent schema",
    emphasis: "important",
  },

  // -------------------------------------------------------------------------
  // Verified Answers
  // -------------------------------------------------------------------------
  {
    id: "va-identify-questions",
    section: "Verified Answers",
    text: "Identify the most common questions from your team",
  },
  {
    id: "va-test-triggers",
    section: "Verified Answers",
    text: "Test trigger questions for both exact and semantic matching",
  },

  // -------------------------------------------------------------------------
  // AI Instructions
  // -------------------------------------------------------------------------
  {
    id: "instr-no-contradictions",
    section: "AI Instructions",
    text: "Ensure instructions do not contradict verified answer configurations",
  },

  // -------------------------------------------------------------------------
  // Data Agent Configuration
  // -------------------------------------------------------------------------
  {
    id: "agent-same-tables",
    section: "Data Agent Configuration",
    text: "Select the same tables in Data Agent that are defined in Prep for AI > AI Data Schema",
    emphasis: "important",
  },
  {
    id: "agent-test-before-instructions",
    section: "Data Agent Configuration",
    text: "Test and validate responses before adding AI instructions",
  },
  {
    id: "agent-cross-source-only",
    section: "Data Agent Configuration",
    text: "Add Data Agent instructions only for guidance that applies across ALL data sources",
  },
  {
    id: "agent-routing",
    section: "Data Agent Configuration",
    text: "Add routing instructions when using multiple semantic models, or a semantic model alongside other source types",
  },
  {
    id: "agent-instruction-limits",
    section: "Data Agent Configuration",
    text: "Limit Data Agent instructions to response formatting, cross-source routing, common abbreviations, and tone",
  },
  {
    id: "agent-no-model-specifics",
    section: "Data Agent Configuration",
    text: "Do NOT add semantic-model-specific instructions at the Data Agent level",
    emphasis: "warning",
  },

  // -------------------------------------------------------------------------
  // Testing and Validation
  // -------------------------------------------------------------------------
  {
    id: "test-baseline",
    section: "Testing and Validation",
    text: "Test responses before adding AI instructions to identify gaps",
  },
  {
    id: "test-review-dax",
    section: "Testing and Validation",
    text: "Review the DAX query in each response to verify accuracy and DAX pattern",
  },
  {
    id: "test-isolate-config",
    section: "Testing and Validation",
    text: "When results are incorrect, identify which configuration needs adjustment: AI data schema, verified answers, or AI instructions",
  },
  {
    id: "test-latency",
    section: "Testing and Validation",
    text: "When responses take longer than expected, analyze DAX performance and keep AI instructions concise",
  },
  {
    id: "test-in-schema-fields",
    section: "Testing and Validation",
    text: "Test with fields inside the AI data schema -- these should return answers",
  },
  {
    id: "test-verified-answers",
    section: "Testing and Validation",
    text: "Verify trigger questions return the correct verified answers",
  },
  {
    id: "test-sdk-evaluation",
    section: "Testing and Validation",
    text: "Use the Fabric Data Agent Python SDK for automated evaluation against ground truth",
    docUrl: "https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk",
    docLabel: "Data Agent Python SDK",
  },
  {
    id: "test-diagnostics",
    section: "Testing and Validation",
    text: "Download and review the diagnostics logs when debugging",
    docUrl: "https://learn.microsoft.com/en-us/fabric/data-science/evaluate-data-agent#diagnostics-button",
    docLabel: "Diagnostics",
  },
  {
    id: "test-iterate",
    section: "Testing and Validation",
    text: "Iterate on configuration based on validation findings",
  },
  {
    id: "test-lifecycle",
    section: "Testing and Validation",
    text: "Use Git and Deployment Pipelines for Data Agent lifecycle management",
  },
  {
    id: "test-agent-description",
    section: "Testing and Validation",
    text: "Add a Data Agent description before publishing",
  },
  {
    id: "test-m365-publishing",
    section: "Testing and Validation",
    text: "Add publishing instructions if the Data Agent is used in Microsoft 365 Copilot",
    docUrl: "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-microsoft-365-copilot#control-how-microsoft-365-copilot-handles-the-output-from-fabric-data-agent",
    docLabel: "M365 Copilot output control",
  },
];

/** Manual items grouped in checklist order, skipping sections with no items. */
export function manualItemsBySection(): { section: string; items: ManualItem[] }[] {
  return MANUAL_SECTIONS.map((section) => ({
    section,
    items: MANUAL_ITEMS.filter((item) => item.section === section),
  })).filter((group) => group.items.length > 0);
}
