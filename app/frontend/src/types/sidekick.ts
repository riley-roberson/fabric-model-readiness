/** How a step proves itself done. */
export type EvidenceKind = "manual" | "artifact" | "lint" | "naming" | "derived" | "external";

export type StepStatus = "pending" | "done" | "skipped";

export interface ProcessStep {
  id: string;
  index: number;
  text: string;
  detail: string;
  evidence: EvidenceKind;
  checks: string[];
  artifacts: string[];
  layer: string;
  optional_when: string;
  /** Not in the source process document -- awaiting the doc owner's ratification. */
  proposed: boolean;
  auto_verifiable: boolean;
}

export interface ProcessGate {
  id: string;
  text: string;
  requires: string[];
}

export interface ProcessStage {
  id: string;
  phase: string;
  title: string;
  proposed: boolean;
  proposal_note: string;
  steps: ProcessStep[];
  gate: ProcessGate | null;
}

export interface ProcessDefinition {
  source_document: string;
  doc_revision: string;
  total_steps: number;
  stages: ProcessStage[];
}

export interface StepStateEntry {
  state: StepStatus;
  note: string;
  reason: string;
  updated_at: string;
}

export interface GateStateEntry {
  passed: boolean;
  attested_by: string;
  attested_at: string;
  note: string;
  /** Prerequisite step ids still outstanding. Non-empty means the gate is shut. */
  blocking: string[];
}

export interface Completion {
  total: number;
  resolved: number;
  percent: number;
}

export interface ProjectState {
  name: string;
  root_path: string;
  model_path: string;
  size: "small" | "medium" | "large";
  current_stage: string;
  current_stage_index: number;
  stage_count: number;
  steps: Record<string, StepStateEntry>;
  gates: Record<string, GateStateEntry>;
  completion: Completion;
  stage_completion: Completion & { stage: string };
  next_step: { id: string; index: number; text: string; stage_id: string } | null;
}

export interface StageProgress {
  stage: string;
  checks_in_play: number;
  checks_passing: number;
  checks_failing: number;
  percent: number;
  findings: number;
  /** Findings held back because their check is not meaningful yet. */
  suppressed: number;
}

export interface StageFinding {
  id: string;
  check: string;
  category: string;
  severity: string;
  object: string;
  message: string;
  recommendation: string;
  auto_fixable: boolean;
}

export interface StageFindings {
  stage: string;
  progress: StageProgress;
  findings: StageFinding[];
  message?: string;
}
