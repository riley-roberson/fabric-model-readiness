import { useMemo } from "react";
import type { Finding, Severity } from "../scanner/types";
import { SEVERITY_ORDER } from "../scanner/types";
import { FindingCard } from "./FindingCard";
import { FindingBundle } from "./FindingBundle";

interface FindingsPanelProps {
  findings: Finding[];
}

const SECTION_COLORS: Record<Severity, { border: string; text: string; dot: string }> = {
  critical: { border: "border-red-200", text: "text-red-600", dot: "bg-red-500" },
  high: { border: "border-orange-200", text: "text-orange-600", dot: "bg-orange-500" },
  medium: { border: "border-amber-200", text: "text-amber-600", dot: "bg-amber-500" },
  low: { border: "border-blue-200", text: "text-blue-600", dot: "bg-blue-500" },
  info: { border: "border-gray-300", text: "text-gray-500", dot: "bg-gray-400" },
};

interface CheckGroup {
  check: string;
  findings: Finding[];
}

function groupByCheck(findings: Finding[]): CheckGroup[] {
  const map = new Map<string, Finding[]>();
  for (const f of findings) {
    const arr = map.get(f.check);
    if (arr) arr.push(f);
    else map.set(f.check, [f]);
  }
  return Array.from(map.entries()).map(([check, items]) => ({ check, findings: items }));
}

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
        <p className="text-sm text-gray-500">
          <span className="font-bold text-gray-900">{findings.length}</span> findings
          {autoFixableCount > 0 && (
            <span className="ml-2 text-brand-teal">({autoFixableCount} auto-fixable)</span>
          )}
        </p>
      </div>

      {SEVERITY_ORDER.map((severity) => {
        const items = grouped[severity];
        if (items.length === 0) return null;
        const colors = SECTION_COLORS[severity];
        const bundles = groupByCheck(items);
        return (
          <div key={severity} className="mb-4">
            <div className={`flex items-center gap-2 mb-2 pb-1.5 border-b ${colors.border}`}>
              <div className={`w-2 h-2 rounded-full ${colors.dot}`} />
              <h3 className={`text-xs font-bold uppercase tracking-widest ${colors.text}`}>{severity}</h3>
              <span className="text-xs text-gray-400">({items.length})</span>
            </div>
            {bundles.map((group) =>
              group.findings.length === 1 ? (
                <FindingCard key={group.findings[0].id} finding={group.findings[0]} />
              ) : (
                <FindingBundle key={group.check} check={group.check} findings={group.findings} />
              ),
            )}
          </div>
        );
      })}
    </div>
  );
}
