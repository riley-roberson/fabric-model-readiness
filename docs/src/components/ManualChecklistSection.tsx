import { useState } from "react";
import type { ManualItem } from "../checklist/manual";
import { MANUAL_CHECKLIST_SOURCE, manualItemsBySection } from "../checklist/manual";
import type { ManualStats } from "../hooks/useChecklist";

interface ManualChecklistSectionProps {
  stats: ManualStats;
  isManualChecked: (id: string) => boolean;
  onToggle: (id: string) => void;
  hideAddressed: boolean;
}

const EMPHASIS_BADGE: Record<string, { label: string; className: string }> = {
  important: { label: "IMPORTANT", className: "bg-amber-50 text-amber-700 border-amber-200" },
  warning: { label: "DO NOT", className: "bg-red-50 text-red-700 border-red-200" },
};

export function ManualChecklistSection({
  stats,
  isManualChecked,
  onToggle,
  hideAddressed,
}: ManualChecklistSectionProps) {
  const [collapsed, setCollapsed] = useState(false);
  const groups = manualItemsBySection();

  return (
    <div className="mb-4">
      {/* Section header */}
      <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-gray-300">
        <div className="w-2 h-2 rounded-full bg-brand-teal" />
        <h3 className="text-xs font-bold uppercase tracking-widest text-gray-600">
          Manual Verification
        </h3>
        <span className="text-xs text-gray-400 tabular-nums">
          ({stats.checked}/{stats.total})
        </span>
        <button
          className="ml-auto text-xs text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? "Show" : "Hide"}
        </button>
      </div>

      <p className="text-xs text-gray-500 leading-relaxed mb-3">
        Steps Scout cannot verify from the model files -- notebook runs, Data Agent setup, and live
        testing. Tracked here for completeness and{" "}
        <span className="font-semibold text-gray-700">not counted toward the score</span>. Source:{" "}
        <a
          href={MANUAL_CHECKLIST_SOURCE}
          target="_blank"
          rel="noreferrer"
          className="text-brand-teal hover:underline"
        >
          Fabric Data Agent checklist
        </a>
        .
      </p>

      {!collapsed && (
        <div className="space-y-3">
          {groups.map(({ section, items }) => {
            const visible = hideAddressed ? items.filter((i) => !isManualChecked(i.id)) : items;
            if (visible.length === 0) return null;
            const done = items.filter((i) => isManualChecked(i.id)).length;

            return (
              <div key={section} className="card px-3 py-2.5">
                <div className="flex items-center gap-2 mb-1.5">
                  <h4 className="text-xs font-bold text-gray-700">{section}</h4>
                  <span className="text-xs text-gray-400 tabular-nums">
                    {done}/{items.length}
                  </span>
                </div>
                <div className="space-y-0.5">
                  {visible.map((item) => (
                    <ManualRow
                      key={item.id}
                      item={item}
                      checked={isManualChecked(item.id)}
                      onToggle={() => onToggle(item.id)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface ManualRowProps {
  item: ManualItem;
  checked: boolean;
  onToggle: () => void;
}

function ManualRow({ item, checked, onToggle }: ManualRowProps) {
  const badge = item.emphasis ? EMPHASIS_BADGE[item.emphasis] : null;

  return (
    <div className="flex items-start gap-2 py-1 group">
      <input
        type="checkbox"
        id={item.id}
        checked={checked}
        onChange={onToggle}
        className="w-3 h-3 mt-1 rounded border-gray-300 bg-white text-brand-emerald focus:ring-brand-emerald focus:ring-offset-0 cursor-pointer flex-shrink-0"
      />
      <label htmlFor={item.id} className="flex-1 min-w-0 cursor-pointer">
        {badge && (
          <span
            className={`inline-block mr-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold border align-middle ${badge.className}`}
          >
            {badge.label}
          </span>
        )}
        <span
          className={`text-xs leading-relaxed ${
            checked ? "line-through text-gray-400" : "text-gray-700 group-hover:text-gray-900"
          }`}
        >
          {item.text}
        </span>
        {item.docUrl && (
          <>
            {" "}
            <a
              href={item.docUrl}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-brand-teal hover:underline whitespace-nowrap"
            >
              {item.docLabel ?? "docs"} &#8599;
            </a>
          </>
        )}
      </label>
    </div>
  );
}
