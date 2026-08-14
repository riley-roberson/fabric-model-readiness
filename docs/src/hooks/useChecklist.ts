import { useCallback, useMemo, useState } from "react";
import type { Finding, Severity } from "../scanner/types";
import { SEVERITY_ORDER } from "../scanner/types";
import { MANUAL_ITEMS } from "../checklist/manual";

/** Stable key that survives page reloads (finding IDs reset each load). */
function stableKey(f: Finding): string {
  return `${f.category}::${f.check}::${f.object}`;
}

function storageKey(modelName: string): string {
  return `scout-checklist:${modelName}`;
}

/** Manual items persist separately -- they survive a rescan unchanged. */
function manualStorageKey(modelName: string): string {
  return `scout-manual-checklist:${modelName}`;
}

function loadSet(key: string): Set<string> {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return new Set();
    const arr: unknown = JSON.parse(raw);
    if (Array.isArray(arr)) return new Set(arr.filter((v): v is string => typeof v === "string"));
  } catch { /* ignore corrupt data */ }
  return new Set();
}

function saveSet(key: string, checked: Set<string>): void {
  try {
    localStorage.setItem(key, JSON.stringify([...checked]));
  } catch { /* quota exceeded -- silently ignore */ }
}

function loadChecked(modelName: string): Set<string> {
  return loadSet(storageKey(modelName));
}

function saveChecked(modelName: string, checked: Set<string>): void {
  saveSet(storageKey(modelName), checked);
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

/** Manual items are tracked but never scored, so they get their own tally. */
export interface ManualStats {
  total: number;
  checked: number;
  percent: number;
}

export interface UseChecklistReturn {
  isChecked: (finding: Finding) => boolean;
  toggle: (finding: Finding) => void;
  clearAll: () => void;
  stats: ChecklistStats;
  isManualChecked: (id: string) => boolean;
  toggleManual: (id: string) => void;
  manualStats: ManualStats;
}

export function useChecklist(findings: Finding[], modelName: string): UseChecklistReturn {
  const [checked, setChecked] = useState<Set<string>>(() => loadChecked(modelName));
  const [manualChecked, setManualChecked] = useState<Set<string>>(
    () => loadSet(manualStorageKey(modelName)),
  );

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

  const isManualChecked = useCallback(
    (id: string) => manualChecked.has(id),
    [manualChecked],
  );

  const toggleManual = useCallback(
    (id: string) => {
      setManualChecked((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        saveSet(manualStorageKey(modelName), next);
        return next;
      });
    },
    [modelName],
  );

  const clearAll = useCallback(() => {
    setChecked(new Set());
    saveChecked(modelName, new Set());
    setManualChecked(new Set());
    saveSet(manualStorageKey(modelName), new Set());
  }, [modelName]);

  const manualStats = useMemo<ManualStats>(() => {
    const total = MANUAL_ITEMS.length;
    const checkedCount = MANUAL_ITEMS.filter((item) => manualChecked.has(item.id)).length;
    return {
      total,
      checked: checkedCount,
      percent: total === 0 ? 100 : Math.round((checkedCount / total) * 100),
    };
  }, [manualChecked]);

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

  return { isChecked, toggle, clearAll, stats, isManualChecked, toggleManual, manualStats };
}
