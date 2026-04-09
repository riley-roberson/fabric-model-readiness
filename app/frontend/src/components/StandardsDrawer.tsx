import { useEffect, useRef } from "react";

interface StandardsDrawerProps {
  open: boolean;
  onClose: () => void;
}

const categories = [
  { name: "AI Preparation", weight: 20, description: "Schema visibility, Copilot instructions, verified answers, noise field exclusion" },
  { name: "Metadata Completeness", weight: 20, description: "Table/column/measure descriptions, synonyms, data categories" },
  { name: "Schema Design", weight: 15, description: "Star schema structure, table naming, display folders, wide table detection" },
  { name: "Measures & Calculations", weight: 15, description: "Explicit DAX measures, time intelligence, qualified references, no duplicates" },
  { name: "Org Standards", weight: 10, description: "Display folders, RLS roles, date table marked, USERELATIONSHIP usage" },
  { name: "Relationships", weight: 10, description: "No orphaned tables, no bidirectional or ambiguous paths, inactive relationship handling" },
  { name: "Data Types", weight: 5, description: "Correct summarization settings, sort-by-column, no unnecessary floats" },
  { name: "Data Consistency", weight: 5, description: "No year-partitioned tables, consistent naming patterns" },
];

const ratings = [
  { range: "90 - 100", label: "AI-Ready", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
  { range: "75 - 89", label: "Mostly Ready", color: "text-lime-400", bg: "bg-lime-500/10", border: "border-lime-500/20" },
  { range: "50 - 74", label: "Needs Work", color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
  { range: "0 - 49", label: "Not Ready", color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20" },
];

const keyStandards = [
  { title: "Star Schema Required", detail: "All models must be star schemas -- no flat tables or snowflakes." },
  { title: "Fact Tables Hidden", detail: "Fact tables hidden from users; only surrogate keys + fact columns." },
  { title: "Surrogate Keys Hidden", detail: "Surrogate keys on dimension tables must be hidden." },
  { title: "Display Folders Required", detail: "Columns and measures must be organized in display folders." },
  { title: "No Default Aggregations", detail: "All aggregations must be explicit DAX measures." },
  { title: "Dedicated Measure Tables", detail: "All measures stored in dedicated measure tables." },
  { title: "Fully Qualified References", detail: "Always use 'Table'[Column] syntax, never unqualified." },
  { title: "No Unnecessary Floats", detail: "Avoid float data types unless strictly necessary." },
  { title: "Date Table Marked", detail: "Calendar table must be marked as date table; no auto-generated date tables." },
  { title: "RLS Roles Defined", detail: "At minimum Admin and General roles must be defined." },
  { title: "USERELATIONSHIP Preferred", detail: "Use USERELATIONSHIP instead of duplicating dimension tables." },
  { title: "No Bidirectional Relationships", detail: "Use CROSSFILTER in DAX instead of bidirectional relationships." },
];

export function StandardsDrawer({ open, onClose }: StandardsDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    // Delay listener to avoid closing immediately on the opening click
    const id = setTimeout(() => document.addEventListener("mousedown", handleClick), 0);
    return () => {
      clearTimeout(id);
      document.removeEventListener("mousedown", handleClick);
    };
  }, [open, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/50 z-40 transition-opacity duration-200 ${
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className={`fixed top-0 right-0 h-full w-[420px] max-w-[90vw] z-50 bg-slate-900 border-l border-slate-700 shadow-2xl transform transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Drawer header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-base font-bold text-white">Scoring Standards</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto h-[calc(100%-57px)] px-5 py-4 space-y-6">

          {/* How scoring works */}
          <section>
            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-2">How Scoring Works</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Each model is scored 0-100 across eight categories. Within each category, the score equals
              the ratio of passing checks to total checks, multiplied by the category weight.
              Critical-severity findings count as <span className="text-red-400 font-semibold">2x failures</span>,
              applying a heavier penalty.
            </p>
          </section>

          {/* Category weights */}
          <section>
            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Category Weights</h3>
            <div className="space-y-2">
              {categories.map((cat) => (
                <div key={cat.name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-300">{cat.name}</span>
                    <span className="text-xs font-bold text-blue-400 tabular-nums">{cat.weight}%</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 mb-1">
                    <div
                      className="h-1.5 rounded-full bg-blue-500/60"
                      style={{ width: `${cat.weight * 5}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-slate-500 leading-snug">{cat.description}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Rating thresholds */}
          <section>
            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Rating Thresholds</h3>
            <div className="grid grid-cols-2 gap-2">
              {ratings.map((r) => (
                <div key={r.label} className={`${r.bg} ${r.border} border rounded-lg px-3 py-2`}>
                  <p className={`text-sm font-bold ${r.color}`}>{r.range}</p>
                  <p className="text-xs text-slate-400">{r.label}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Severity levels */}
          <section>
            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Severity Levels</h3>
            <div className="space-y-1.5">
              {[
                { level: "Critical", desc: "Fundamental issues blocking AI readiness. Counts as 2x penalty.", color: "text-red-400", dot: "bg-red-400" },
                { level: "High", desc: "Significant gaps that degrade Copilot quality.", color: "text-orange-400", dot: "bg-orange-400" },
                { level: "Medium", desc: "Moderate issues that should be addressed.", color: "text-amber-400", dot: "bg-amber-400" },
                { level: "Low", desc: "Minor improvements for completeness.", color: "text-blue-400", dot: "bg-blue-400" },
                { level: "Info", desc: "Informational observations, no score impact.", color: "text-slate-400", dot: "bg-slate-400" },
              ].map((s) => (
                <div key={s.level} className="flex items-start gap-2">
                  <span className={`${s.dot} w-2 h-2 rounded-full mt-1.5 shrink-0`} />
                  <div>
                    <span className={`text-xs font-bold ${s.color}`}>{s.level}</span>
                    <span className="text-xs text-slate-500 ml-1.5">{s.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Key standards */}
          <section>
            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Key Standards Checked</h3>
            <div className="space-y-2">
              {keyStandards.map((s) => (
                <div key={s.title} className="bg-slate-800/50 rounded-lg px-3 py-2">
                  <p className="text-xs font-semibold text-slate-200">{s.title}</p>
                  <p className="text-[11px] text-slate-500 leading-snug mt-0.5">{s.detail}</p>
                </div>
              ))}
            </div>
          </section>

          {/* References */}
          <section className="pb-4">
            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-2">References</h3>
            <ul className="space-y-1 text-xs text-slate-400">
              <li>Microsoft: Prepare Semantic Model for Copilot</li>
              <li>Microsoft: Optimize Semantic Model for Copilot</li>
              <li>Microsoft: Semantic Model Best Practices for Data Agent</li>
              <li>Organization: Power BI Standards document</li>
            </ul>
          </section>
        </div>
      </div>
    </>
  );
}
