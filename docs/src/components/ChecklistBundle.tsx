import { useState, useRef, useEffect } from "react";
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

interface ChecklistBundleProps {
  check: string;
  findings: Finding[];
  isChecked: (finding: Finding) => boolean;
  onToggle: (finding: Finding) => void;
}

export function ChecklistBundle({
  check,
  findings,
  isChecked,
  onToggle,
}: ChecklistBundleProps) {
  const [expanded, setExpanded] = useState(false);
  const checkboxRef = useRef<HTMLInputElement>(null);
  const sample = findings[0];

  const checkedCount = findings.filter(isChecked).length;
  const allChecked = checkedCount === findings.length;
  const someChecked = checkedCount > 0 && !allChecked;

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = someChecked;
    }
  }, [someChecked]);

  const handleMasterToggle = () => {
    for (const f of findings) {
      if (allChecked) {
        if (isChecked(f)) onToggle(f);
      } else {
        if (!isChecked(f)) onToggle(f);
      }
    }
  };

  const autoFixableCount = findings.filter((f) => f.auto_fixable).length;

  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white hover:border-gray-300 transition-colors duration-100 mb-1.5 overflow-hidden ${
        allChecked ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-center gap-2 px-3 py-2.5">
        <input
          ref={checkboxRef}
          type="checkbox"
          checked={allChecked}
          onChange={handleMasterToggle}
          className="w-3.5 h-3.5 rounded border-gray-300 bg-white text-brand-emerald focus:ring-brand-emerald focus:ring-offset-0 cursor-pointer flex-shrink-0"
        />

        <button
          className="flex-1 min-w-0 text-left flex items-center gap-2"
          onClick={() => setExpanded(!expanded)}
        >
          <span
            className={`${BADGE_CLASS[sample.severity]} text-[10px] py-0.5 px-1.5`}
          >
            {sample.severity}
          </span>

          <div className="flex-1 min-w-0">
            <p
              className={`text-sm font-medium truncate leading-tight ${
                allChecked ? "line-through text-gray-400" : "text-gray-900"
              }`}
            >
              {formatCheckName(check)}
            </p>
            <p className="text-xs text-gray-500 truncate leading-tight mt-0.5">
              {checkedCount}/{findings.length} addressed
            </p>
          </div>

          {autoFixableCount > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-brand-berry/10 text-brand-berry border border-brand-berry/20 flex-shrink-0">
              FIX
            </span>
          )}

          <svg
            width="12"
            height="12"
            className={`text-gray-400 transition-transform duration-100 flex-shrink-0 ${
              expanded ? "rotate-90" : ""
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8.25 4.5l7.5 7.5-7.5 7.5"
            />
          </svg>
        </button>
      </div>

      {expanded && (
        <div className="border-t border-gray-200 px-3 pb-2 pt-1">
          {sample.recommendation && (
            <div className="mb-2 mt-1 p-2.5 rounded-lg bg-gray-50 border border-gray-200 ml-5">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-bold mb-1">
                Recommendation
              </p>
              <p className="text-sm text-gray-700 leading-relaxed">
                {sample.recommendation}
              </p>
            </div>
          )}

          <div className="space-y-0.5 ml-5">
            {findings.map((f) => (
              <label
                key={f.id}
                className="flex items-center gap-2 py-1 cursor-pointer group"
              >
                <input
                  type="checkbox"
                  checked={isChecked(f)}
                  onChange={() => onToggle(f)}
                  className="w-3 h-3 rounded border-gray-300 bg-white text-brand-emerald focus:ring-brand-emerald focus:ring-offset-0 cursor-pointer flex-shrink-0"
                />
                <span
                  className={`text-xs truncate ${
                    isChecked(f)
                      ? "line-through text-gray-400"
                      : "text-gray-600 group-hover:text-gray-900"
                  }`}
                >
                  {f.object}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
