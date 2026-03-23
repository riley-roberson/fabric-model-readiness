import type { ChecklistStats } from "../hooks/useChecklist";

export type ViewMode = "findings" | "checklist";

interface ViewToggleProps {
  mode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
  stats: ChecklistStats;
}

export function ViewToggle({ mode, onModeChange, stats }: ViewToggleProps) {
  return (
    <div className="flex gap-1 mb-4 p-1 rounded-lg bg-slate-900 border border-slate-800 w-fit">
      <button
        className={`btn-tab ${mode === "findings" ? "btn-tab-active" : ""}`}
        onClick={() => onModeChange("findings")}
      >
        Findings
      </button>
      <button
        className={`btn-tab ${mode === "checklist" ? "btn-tab-active" : ""}`}
        onClick={() => onModeChange("checklist")}
      >
        Checklist
        {stats.total > 0 && (
          <span className="ml-1.5 text-[10px] tabular-nums text-slate-500">
            {stats.checked}/{stats.total}
          </span>
        )}
      </button>
    </div>
  );
}
