import { useState } from "react";
import type { Finding, Severity } from "../scanner/types";

const BADGE_CLASS: Record<Severity, string> = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
  info: "badge-info",
};

function formatCheckName(check: string): string {
  return check
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bAi\b/g, "AI")
    .replace(/\bRls\b/g, "RLS")
    .replace(/\bDax\b/g, "DAX");
}

interface FindingBundleProps {
  check: string;
  findings: Finding[];
}

export function FindingBundle({ check, findings }: FindingBundleProps) {
  const [expanded, setExpanded] = useState(false);
  const sample = findings[0];
  const autoFixableCount = findings.filter((f) => f.auto_fixable).length;

  return (
    <div className="rounded-lg border border-gray-200 bg-white hover:border-gray-300 transition-colors duration-100 mb-1.5 overflow-hidden">
      <button
        className="w-full text-left px-3 py-2.5 flex items-center gap-2"
        onClick={() => setExpanded(!expanded)}
      >
        <svg
          width="12"
          height="12"
          className={`text-gray-400 transition-transform duration-100 flex-shrink-0 ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>

        <span className={`${BADGE_CLASS[sample.severity]} text-[10px] py-0.5 px-1.5`}>
          {sample.severity}
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate leading-tight">
            {formatCheckName(check)}
          </p>
          <p className="text-xs text-gray-500 leading-tight mt-0.5">
            {findings.length} items
          </p>
        </div>

        {autoFixableCount > 0 && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-brand-berry/10 text-brand-berry border border-brand-berry/20 flex-shrink-0">
            FIX
          </span>
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-2 border-t border-gray-200">
          {sample.recommendation && (
            <div className="mb-3 p-2.5 rounded-lg bg-gray-50 border border-gray-200">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-bold mb-1">
                Recommendation
              </p>
              <p className="text-sm text-gray-700 leading-relaxed">{sample.recommendation}</p>
            </div>
          )}

          <div className="space-y-0.5">
            {findings.map((f) => (
              <div
                key={f.id}
                className="text-xs text-gray-600 flex items-center gap-1.5 py-0.5"
              >
                <span className="w-1 h-1 rounded-full bg-gray-400 flex-shrink-0" />
                <span className="truncate">{f.object}</span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3 mt-3 pt-2 border-t border-gray-100">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500 font-bold">Category:</span>
              <span className="text-xs text-gray-600">
                {sample.category.replace(/_/g, " ")}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500 font-bold">Check:</span>
              <span className="text-xs text-gray-600">{sample.check}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
