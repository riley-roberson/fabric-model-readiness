import { useState } from "react";
import type { Finding, Severity } from "../scanner/types";

const BADGE_CLASS: Record<Severity, string> = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
  info: "badge-info",
};

interface ChecklistItemProps {
  finding: Finding;
  checked: boolean;
  onToggle: () => void;
}

export function ChecklistItem({ finding, checked, onToggle }: ChecklistItemProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white hover:border-gray-300 transition-colors duration-100 mb-1.5 overflow-hidden ${
        checked ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-center gap-2 px-3 py-2.5">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          className="w-3.5 h-3.5 rounded border-gray-300 bg-white text-brand-emerald focus:ring-brand-emerald focus:ring-offset-0 cursor-pointer flex-shrink-0"
        />

        {/* Main content -- clickable to expand */}
        <button
          className="flex-1 min-w-0 text-left flex items-center gap-2"
          onClick={() => setExpanded(!expanded)}
        >
          <span className={`${BADGE_CLASS[finding.severity]} text-[10px] py-0.5 px-1.5`}>
            {finding.severity}
          </span>

          <div className="flex-1 min-w-0">
            <p className={`text-sm font-medium truncate leading-tight ${checked ? "line-through text-gray-400" : "text-gray-900"}`}>
              {finding.message}
            </p>
            <p className="text-xs text-gray-500 truncate leading-tight mt-0.5">{finding.object}</p>
          </div>

          {finding.auto_fixable && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-brand-berry/10 text-brand-berry border border-brand-berry/20 flex-shrink-0">
              FIX
            </span>
          )}

          {/* Expand chevron on right */}
          <svg
            width="12"
            height="12"
            className={`text-gray-400 transition-transform duration-100 flex-shrink-0 ${expanded ? "rotate-90" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-2 border-t border-gray-200 ml-6">
          {finding.recommendation && (
            <div className="mb-3 p-2.5 rounded-lg bg-gray-50 border border-gray-200">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-bold mb-1">Recommendation</p>
              <p className="text-sm text-gray-700 leading-relaxed">{finding.recommendation}</p>
            </div>
          )}

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500 font-bold">Category:</span>
              <span className="text-xs text-gray-600">{finding.category.replace(/_/g, " ")}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500 font-bold">Check:</span>
              <span className="text-xs text-gray-600">{finding.check}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
