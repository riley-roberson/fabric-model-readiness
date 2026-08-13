import type { ChecklistStats, ManualStats } from "../hooks/useChecklist";
import type { Severity } from "../scanner/types";

interface ChecklistProgressProps {
  stats: ChecklistStats;
  onClearAll: () => void;
  /** Omitted in the org profile, where no manual items are shown. */
  manualStats?: ManualStats;
}

const SEV_COLORS: Record<Severity, string> = {
  critical: "text-red-600",
  high: "text-orange-600",
  medium: "text-amber-600",
  low: "text-blue-600",
  info: "text-gray-500",
};

export function ChecklistProgress({ stats, onClearAll, manualStats }: ChecklistProgressProps) {
  return (
    <div className="card px-4 py-3 mb-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-gray-500">
          <span className="font-bold text-gray-900">{stats.checked}</span> of{" "}
          <span className="font-bold text-gray-900">{stats.total}</span> findings addressed
          <span className="ml-1 text-gray-400">({stats.percent}%)</span>
        </p>
        {stats.checked > 0 && (
          <button
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
            onClick={onClearAll}
          >
            Clear all
          </button>
        )}
      </div>

      <div className="w-full bg-gray-200 rounded-full h-1.5 mb-3 overflow-hidden">
        <div
          className="h-1.5 rounded-full bg-gradient-to-r from-brand-emerald to-brand-teal transition-all duration-300"
          style={{ width: `${stats.percent}%` }}
        />
      </div>

      <div className="flex gap-3 flex-wrap">
        {stats.bySeverity.map(({ severity, total, checked }) => (
          <span key={severity} className={`text-xs ${SEV_COLORS[severity]}`}>
            {severity}: {checked}/{total}
          </span>
        ))}
      </div>

      {manualStats && (
        <p className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-200">
          Plus{" "}
          <span className="font-semibold text-gray-600">
            {manualStats.checked}/{manualStats.total}
          </span>{" "}
          manual verification steps -- tracked below, not scored.
        </p>
      )}
    </div>
  );
}
