import { useMemo, useState } from "react";
import type { Finding, Severity } from "../scanner/types";
import { SEVERITY_ORDER } from "../scanner/types";
import type { UseChecklistReturn } from "../hooks/useChecklist";
import { ChecklistProgress } from "./ChecklistProgress";
import { ChecklistItem } from "./ChecklistItem";
import { ChecklistBundle } from "./ChecklistBundle";

interface ChecklistPanelProps {
  findings: Finding[];
  checklist: UseChecklistReturn;
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

export function ChecklistPanel({ findings, checklist }: ChecklistPanelProps) {
  const [hideAddressed, setHideAddressed] = useState(false);
  const { isChecked, toggle, clearAll, stats } = checklist;

  const grouped = useMemo(() => {
    const groups: Record<Severity, Finding[]> = { critical: [], high: [], medium: [], low: [], info: [] };
    for (const f of findings) {
      if (hideAddressed && isChecked(f)) continue;
      groups[f.severity].push(f);
    }
    return groups;
  }, [findings, hideAddressed, isChecked]);

  const allDone = stats.checked === stats.total && stats.total > 0;

  return (
    <div>
      <ChecklistProgress stats={stats} onClearAll={clearAll} />

      <div className="flex items-center gap-2 mb-4">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={hideAddressed}
            onChange={(e) => setHideAddressed(e.target.checked)}
            className="w-3 h-3 rounded border-gray-300 bg-white text-brand-emerald focus:ring-brand-emerald focus:ring-offset-0 cursor-pointer"
          />
          <span className="text-xs text-gray-500">Hide addressed items</span>
        </label>
      </div>

      {allDone && !hideAddressed && (
        <div className="card p-6 text-center mb-4">
          <p className="text-sm font-bold text-emerald-600 mb-1">All findings addressed</p>
          <p className="text-xs text-gray-500">Every item on the checklist has been marked as addressed.</p>
        </div>
      )}

      {allDone && hideAddressed && (
        <div className="card p-6 text-center mb-4">
          <p className="text-sm font-bold text-emerald-600 mb-1">All findings addressed</p>
          <p className="text-xs text-gray-500">
            Uncheck "Hide addressed items" to see your completed checklist.
          </p>
        </div>
      )}

      {SEVERITY_ORDER.map((severity) => {
        const items = grouped[severity];
        if (items.length === 0) return null;
        const colors = SECTION_COLORS[severity];
        const sevStats = stats.bySeverity.find((s) => s.severity === severity);
        const checkedInSev = sevStats?.checked ?? 0;
        const totalInSev = sevStats?.total ?? items.length;
        const bundles = groupByCheck(items);

        return (
          <div key={severity} className="mb-4">
            <div className={`flex items-center gap-2 mb-2 pb-1.5 border-b ${colors.border}`}>
              <div className={`w-2 h-2 rounded-full ${colors.dot}`} />
              <h3 className={`text-xs font-bold uppercase tracking-widest ${colors.text}`}>{severity}</h3>
              <span className="text-xs text-gray-400 tabular-nums">
                ({checkedInSev}/{totalInSev})
              </span>
            </div>
            {bundles.map((group) =>
              group.findings.length === 1 ? (
                <ChecklistItem
                  key={group.findings[0].id}
                  finding={group.findings[0]}
                  checked={isChecked(group.findings[0])}
                  onToggle={() => toggle(group.findings[0])}
                />
              ) : (
                <ChecklistBundle
                  key={group.check}
                  check={group.check}
                  findings={group.findings}
                  isChecked={isChecked}
                  onToggle={toggle}
                />
              ),
            )}
          </div>
        );
      })}
    </div>
  );
}
