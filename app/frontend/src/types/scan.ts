import type { Finding, ScanSummary } from "./findings";

export interface ScanResult {
  scan_id: string;
  model_path: string;
  model_name?: string;
  format: string;
  score: number;
  rating: string;
  summary: ScanSummary;
  findings: Finding[];
}

export interface ScanProgress {
  step: string;
  percent: number;
  message: string;
}

export interface ApplyRequest {
  scan_id: string;
  model_name: string;
  decisions: DecisionInput[];
}

export interface DecisionInput {
  finding_id: string;
  action: string;
  reason?: string;
  edited_value?: string;
}

export interface ApplyResult {
  applied: number;
  deferred: number;
  rejected: number;
  new_score: number | null;
  history_path: string;
}

export interface HistorySession {
  session_id: string;
  timestamp: string;
  scan_id: string;
  pre_score: number;
  post_score: number | null;
  changes: HistoryChange[];
}

export interface HistoryChange {
  finding_id: string;
  category: string;
  object: string;
  action: string;
  description: string;
  before: unknown;
  after: unknown;
  reason: string | null;
}

export interface ModelHistory {
  model_name: string;
  sessions: HistorySession[];
}

export type AppScreen = "drop" | "scanning" | "results" | "applied" | "history";
