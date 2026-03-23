import { useCallback, useMemo, useState } from "react";
import type { Finding, Severity } from "../scanner/types";
import { SEVERITY_ORDER } from "../scanner/types";

/** Stable key that survives page reloads (finding IDs reset each load). */
function stableKey(f: Finding): string {
  return `${f.category}::${f.check}::${f.object}`;
}

function storageKey(modelName: string): string {
  return `scout-checklist:${modelName}`;
}

function loadChecked(modelName: string): Set<string> {
  try {
    const raw = localStorage.getItem(storageKey(modelName));
    if (!raw) return new Set();
    const arr: unknown = JSON.parse(raw);
    if (Array.isArray(arr)) return new Set(arr.filter((v): v is string => typeof v === "string"));
  } catch { /* ignore corrupt data */ }
  return new Set();
}

function saveChecked(modelName: string, checked: Set<string>): void {
  try {
    localStorage.setItem(storageKey(modelName), JSON.stringify([...checked]));
  } catch { /* quota exceeded -- silently ignore */ }
}

export interface SeverityStats {
  severity: Severity;
  total: number;
  checked: number;
}

export interface ChecklistStats {
  total: number;
  checked: number;
  percent: number;
  bySeverity: SeverityStats[];
}

export interface UseChecklistReturn {
  isChecked: (finding: Finding) => boolean;
  toggle: (finding: Finding) => void;
  clearAll: () => void;
  stats: ChecklistStats;
}

export function useChecklist(findings: Finding[], modelName: string): UseChecklistReturn {
  const [checked, setChecked] = useState<Set<string>>(() => loadChecked(modelName));

  /** Map finding stable keys for quick membership test. */
  const keySet = useMemo(() => {
    const m = new Map<string, Finding>();
    for (const f of findings) m.set(stableKey(f), f);
    return m;
  }, [findings]);

  const isChecked = useCallback(
    (f: Finding) => checked.has(stableKey(f)),
    [checked],
  );

  const toggle = useCallback(
    (f: Finding) => {
      setChecked((prev) => {
        const next = new Set(prev);
        const key = stableKey(f);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        saveChecked(modelName, next);
        return next;
      });
    },
    [modelName],
  );

  const clearAll = useCallback(() => {
    setChecked(new Set());
    saveChecked(modelName, new Set());
  }, [modelName]);

  const stats = useMemo<ChecklistStats>(() => {
    // Only count keys that correspond to current findings
    let checkedCount = 0;
    for (const key of checked) {
      if (keySet.has(key)) checkedCount++;
    }
    const total = findings.length;
    const percent = total === 0 ? 100 : Math.round((checkedCount / total) * 100);

    const bySeverity: SeverityStats[] = SEVERITY_ORDER.map((severity) => {
      const matching = findings.filter((f) => f.severity === severity);
      const sChecked = matching.filter((f) => checked.has(stableKey(f))).length;
      return { severity, total: matching.length, checked: sChecked };
    }).filter((s) => s.total > 0);

    return { total, checked: checkedCount, percent, bySeverity };
  }, [findings, checked, keySet]);

  return { isChecked, toggle, clearAll, stats };
}
