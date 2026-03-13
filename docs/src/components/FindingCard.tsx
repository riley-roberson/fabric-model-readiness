import { useState } from "react";
import type { Finding, Severity } from "../scanner/types";

const BADGE_CLASS: Record<Severity, string> = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
  info: "badge-info",
};

interface FindingCardProps {
  finding: Finding;
}

export function FindingCard({ finding }: FindingCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 hover:border-slate-700 transition-colors duration-100 mb-1.5 overflow-hidden">
      <button
        className="w-full text-left px-3 py-2.5 flex items-center gap-2"
        onClick={() => setExpanded(!expanded)}
      >
        <svg
          width="12"
          height="12"
          className={`text-slate-600 transition-transform duration-100 flex-shrink-0 ${expanded ? "rotate-90" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>

        <span className={`${BADGE_CLASS[finding.severity]} text-[10px] py-0.5 px-1.5`}>
          {finding.severity}
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate leading-tight">{finding.message}</p>
          <p className="text-xs text-slate-500 truncate leading-tight mt-0.5">{finding.object}</p>
        </div>

        {finding.auto_fixable && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/15 text-blue-400 border border-blue-500/20 flex-shrink-0">
            FIX
          </span>
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-2 border-t border-slate-800/50">
          {finding.recommendation && (
            <div className="mb-3 p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
              <p className="text-xs text-slate-500 uppercase tracking-wider font-bold mb-1">Recommendation</p>
              <p className="text-sm text-slate-300 leading-relaxed">{finding.recommendation}</p>
            </div>
          )}

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-500 font-bold">Category:</span>
              <span className="text-xs text-slate-400">{finding.category.replace(/_/g, " ")}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-500 font-bold">Check:</span>
              <span className="text-xs text-slate-400">{finding.check}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
