import { useMemo } from "react";
import type { Finding, Severity, Disposition } from "@/types/findings";
import { SEVERITY_ORDER } from "@/types/findings";
import { FindingCard } from "./FindingCard";
import type { Decision } from "@/hooks/useDecisions";

interface FindingsPanelProps {
  findings: Finding[];
  decisions: Map<string, Decision>;
  onDecision: (findingId: string, action: Disposition) => void;
  onAcceptAll: (findingIds: string[]) => void;
}

const SECTION_COLORS: Record<Severity, { border: string; text: string; dot: string }> = {
  critical: { border: "border-red-500/30", text: "text-red-400", dot: "bg-red-500" },
  high: { border: "border-orange-500/30", text: "text-orange-400", dot: "bg-orange-500" },
  medium: { border: "border-amber-500/30", text: "text-amber-400", dot: "bg-amber-500" },
  low: { border: "border-blue-500/30", text: "text-blue-400", dot: "bg-blue-500" },
  info: { border: "border-slate-500/30", text: "text-slate-400", dot: "bg-slate-500" },
};

export function FindingsPanel({ findings, decisions, onDecision, onAcceptAll }: FindingsPanelProps) {
  const grouped = useMemo(() => {
    const groups: Record<Severity, Finding[]> = { critical: [], high: [], medium: [], low: [], info: [] };
    for (const f of findings) groups[f.severity].push(f);
    return groups;
  }, [findings]);

  const autoFixableIds = useMemo(
    () => findings.filter((f) => f.auto_fixable).map((f) => f.id),
    [findings]
  );

  return (
    <div>
      <div className="card px-4 py-3 mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-400">
          <span className="font-bold text-slate-200">{findings.length}</span> findings
          {autoFixableIds.length > 0 && (
            <span className="ml-2 text-blue-400">({autoFixableIds.length} auto-fixable)</span>
          )}
        </p>
        <div className="flex gap-2">
          {autoFixableIds.length > 0 && (
            <button className="btn-accept text-xs px-3 py-1.5 rounded-lg" onClick={() => onAcceptAll(autoFixableIds)}>
              Auto-fix ({autoFixableIds.length})
            </button>
          )}
          <button className="btn-ghost text-xs px-3 py-1.5 rounded-lg" onClick={() => onAcceptAll(findings.map((f) => f.id))}>
            Accept All
          </button>
        </div>
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
              <FindingCard
                key={finding.id}
                finding={finding}
                decision={decisions.get(finding.id)?.action}
                onDecision={onDecision}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}
