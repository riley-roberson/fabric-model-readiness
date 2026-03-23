import { useMemo } from "react";
import type { Finding, Severity } from "../scanner/types";
import { SEVERITY_ORDER } from "../scanner/types";
import { FindingCard } from "./FindingCard";

interface FindingsPanelProps {
  findings: Finding[];
}

const SECTION_COLORS: Record<Severity, { border: string; text: string; dot: string }> = {
  critical: { border: "border-red-500/30", text: "text-red-400", dot: "bg-red-500" },
  high: { border: "border-orange-500/30", text: "text-orange-400", dot: "bg-orange-500" },
  medium: { border: "border-amber-500/30", text: "text-amber-400", dot: "bg-amber-500" },
  low: { border: "border-blue-500/30", text: "text-blue-400", dot: "bg-blue-500" },
  info: { border: "border-slate-500/30", text: "text-slate-400", dot: "bg-slate-500" },
};

export function FindingsPanel({ findings }: FindingsPanelProps) {
  const grouped = useMemo(() => {
    const groups: Record<Severity, Finding[]> = { critical: [], high: [], medium: [], low: [], info: [] };
    for (const f of findings) groups[f.severity].push(f);
    return groups;
  }, [findings]);

  const autoFixableCount = useMemo(
    () => findings.filter((f) => f.auto_fixable).length,
    [findings],
  );

  return (
    <div>
      <div className="card px-4 py-3 mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-400">
          <span className="font-bold text-slate-200">{findings.length}</span> findings
          {autoFixableCount > 0 && (
            <span className="ml-2 text-brand-teal">({autoFixableCount} auto-fixable)</span>
          )}
        </p>
      </div>

      {SEVERITY_ORDER.map((severity) => {
        const items = grouped[severity];
        if (items.length === 0) return null;
        const colors = SECTION_COLORS[severity];
        return (
          <div key={severity} className="mb-4">
            <div className={`flex items-center gap-2 mb-2 pb-1.5 border-b ${colors.border}`}>
              <div className={`w-2 h-2 rounded-full ${colors.dot}`} />
              <h3 className={`text-xs font-bold uppercase tracking-widest ${colors.text}`}>{severity}</h3>
              <span className="text-xs text-slate-600">({items.length})</span>
            </div>
            {items.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>
        );
      })}
    </div>
  );
}
