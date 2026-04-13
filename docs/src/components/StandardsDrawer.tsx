import { useEffect, useRef } from "react";

interface StandardsDrawerProps {
  open: boolean;
  onClose: () => void;
}

const categories = [
  { name: "AI Preparation", weight: 20, description: "Schema visibility, Copilot instructions, verified answers, noise field exclusion", profiles: ["ai"] as string[] },
  { name: "Metadata Completeness", weight: 20, description: "Table/column/measure descriptions, synonyms, data categories", profiles: ["ai"] as string[] },
  { name: "Schema Design", weight: 15, description: "Star schema structure, table naming, display folders, wide table detection", profiles: ["ai", "shared"] as string[] },
  { name: "Measures & Calculations", weight: 15, description: "Explicit DAX measures, time intelligence, qualified references, no duplicates", profiles: ["ai", "org", "shared"] as string[] },
  { name: "Org Standards", weight: 10, description: "Display folders, RLS roles, date table marked, USERELATIONSHIP usage", profiles: ["org"] as string[] },
  { name: "Relationships", weight: 10, description: "No orphaned tables, no bidirectional or ambiguous paths, inactive relationship handling", profiles: ["ai", "shared"] as string[] },
  { name: "Data Types", weight: 5, description: "Correct summarization settings, sort-by-column, no unnecessary floats", profiles: ["ai", "org", "shared"] as string[] },
  { name: "Data Consistency", weight: 5, description: "No year-partitioned tables, consistent naming patterns", profiles: ["org"] as string[] },
];

const ratings = [
  { range: "90 - 100", label: "AI-Ready", color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  { range: "75 - 89", label: "Mostly Ready", color: "text-lime-700", bg: "bg-lime-50", border: "border-lime-200" },
  { range: "50 - 74", label: "Needs Work", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  { range: "0 - 49", label: "Not Ready", color: "text-red-700", bg: "bg-red-50", border: "border-red-200" },
];

const keyStandards = [
  { title: "Star Schema Required", detail: "All models must be star schemas -- no flat tables or snowflakes.", profile: "shared" },
  { title: "Fact Tables Hidden", detail: "Fact tables hidden from users; only surrogate keys + fact columns.", profile: "shared" },
  { title: "Surrogate Keys Hidden", detail: "Surrogate keys on dimension tables must be hidden.", profile: "shared" },
  { title: "Display Folders Required", detail: "Columns and measures must be organized in display folders.", profile: "org" },
  { title: "No Default Aggregations", detail: "All aggregations must be explicit DAX measures.", profile: "shared" },
  { title: "Dedicated Measure Tables", detail: "All measures stored in dedicated measure tables.", profile: "org" },
  { title: "Fully Qualified References", detail: "Always use 'Table'[Column] syntax, never unqualified.", profile: "org" },
  { title: "No Unnecessary Floats", detail: "Avoid float data types unless strictly necessary.", profile: "org" },
  { title: "Date Table Marked", detail: "Calendar table must be marked as date table; no auto-generated date tables.", profile: "org" },
  { title: "RLS Roles Defined", detail: "At minimum Admin and General roles must be defined.", profile: "org" },
  { title: "USERELATIONSHIP Preferred", detail: "Use USERELATIONSHIP instead of duplicating dimension tables.", profile: "org" },
  { title: "No Bidirectional Relationships", detail: "Use CROSSFILTER in DAX instead of bidirectional relationships.", profile: "org" },
];

export function StandardsDrawer({ open, onClose }: StandardsDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
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
        className={`fixed inset-0 bg-black/30 z-40 transition-opacity duration-200 ${
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className={`fixed top-0 right-0 h-full w-[420px] max-w-[90vw] z-50 bg-white border-l border-gray-200 shadow-2xl transform transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="text-base font-bold text-gray-900">Scoring Standards</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors"
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
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-2">How Scoring Works</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Each model is scored 0-100 across eight categories. Within each category, the score equals
              the ratio of passing checks to total checks, multiplied by the category weight.
              Critical-severity findings count as <span className="text-red-600 font-semibold">2x failures</span>,
              applying a heavier penalty.
            </p>
            <p className="text-xs text-gray-500 leading-relaxed mt-2">
              When a <span className="text-gray-800 font-semibold">scan profile</span> is active, only matching checks
              are scored. Categories with no remaining checks are dropped and weights
              are <span className="text-gray-800 font-semibold">re-normalized</span> to
              100%, so the same model may score differently under different profiles.
            </p>
          </section>

          {/* Scan profiles */}
          <section>
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">Scan Profiles</h3>
            <div className="space-y-2">
              <div className="bg-violet-50 rounded-lg px-3 py-2.5 border border-violet-200">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-100 text-violet-700">AI</span>
                  <span className="text-xs font-semibold text-gray-800">Microsoft Prep for AI</span>
                </div>
                <p className="text-[11px] text-gray-500 leading-snug">
                  Checks tagged <span className="text-violet-600">ai</span> + <span className="text-gray-700">shared</span>.
                  Focuses on Copilot readiness: descriptions, synonyms, AI schema, instructions, verified answers.
                </p>
              </div>
              <div className="bg-amber-50 rounded-lg px-3 py-2.5 border border-amber-200">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">ORG</span>
                  <span className="text-xs font-semibold text-gray-800">Organizational Standards</span>
                </div>
                <p className="text-[11px] text-gray-500 leading-snug">
                  Checks tagged <span className="text-amber-600">org</span> + <span className="text-gray-700">shared</span>.
                  Focuses on internal conventions: display folders, RLS, DAX patterns, measure tables.
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-200">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">BOTH</span>
                  <span className="text-xs font-semibold text-gray-800">All Checks (Default)</span>
                </div>
                <p className="text-[11px] text-gray-500 leading-snug">
                  Runs every check across all categories. Full 48-check sweep with no filtering.
                </p>
              </div>
            </div>
          </section>

          {/* Category weights */}
          <section>
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">Category Weights</h3>
            <div className="space-y-2">
              {categories.map((cat) => (
                <div key={cat.name}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-semibold text-gray-700">{cat.name}</span>
                      {cat.profiles.map((p) => (
                        <span
                          key={p}
                          className={`text-[9px] font-bold uppercase tracking-wider px-1 py-0.5 rounded ${
                            p === "ai" ? "bg-violet-100 text-violet-700" :
                            p === "org" ? "bg-amber-100 text-amber-700" :
                            "bg-gray-100 text-gray-500"
                          }`}
                        >{p}</span>
                      ))}
                    </div>
                    <span className="text-xs font-bold text-brand-emerald tabular-nums">{cat.weight}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5 mb-1">
                    <div
                      className="h-1.5 rounded-full bg-brand-emerald/60"
                      style={{ width: `${cat.weight * 5}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-gray-400 leading-snug">{cat.description}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Rating thresholds */}
          <section>
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">Rating Thresholds</h3>
            <div className="grid grid-cols-2 gap-2">
              {ratings.map((r) => (
                <div key={r.label} className={`${r.bg} ${r.border} border rounded-lg px-3 py-2`}>
                  <p className={`text-sm font-bold ${r.color}`}>{r.range}</p>
                  <p className="text-xs text-gray-500">{r.label}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Severity levels */}
          <section>
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">Severity Levels</h3>
            <div className="space-y-1.5">
              {[
                { level: "Critical", desc: "Fundamental issues blocking AI readiness. Counts as 2x penalty.", color: "text-red-700", dot: "bg-red-500" },
                { level: "High", desc: "Significant gaps that degrade Copilot quality.", color: "text-orange-700", dot: "bg-orange-500" },
                { level: "Medium", desc: "Moderate issues that should be addressed.", color: "text-amber-700", dot: "bg-amber-500" },
                { level: "Low", desc: "Minor improvements for completeness.", color: "text-blue-700", dot: "bg-blue-500" },
                { level: "Info", desc: "Informational observations, no score impact.", color: "text-gray-600", dot: "bg-gray-400" },
              ].map((s) => (
                <div key={s.level} className="flex items-start gap-2">
                  <span className={`${s.dot} w-2 h-2 rounded-full mt-1.5 shrink-0`} />
                  <div>
                    <span className={`text-xs font-bold ${s.color}`}>{s.level}</span>
                    <span className="text-xs text-gray-500 ml-1.5">{s.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Key standards */}
          <section>
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">Key Standards Checked</h3>
            <div className="space-y-2">
              {keyStandards.map((s) => (
                <div key={s.title} className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                  <div className="flex items-center gap-1.5">
                    <p className="text-xs font-semibold text-gray-800">{s.title}</p>
                    <span
                      className={`text-[9px] font-bold uppercase tracking-wider px-1 py-0.5 rounded ${
                        s.profile === "ai" ? "bg-violet-100 text-violet-700" :
                        s.profile === "org" ? "bg-amber-100 text-amber-700" :
                        "bg-gray-100 text-gray-500"
                      }`}
                    >{s.profile}</span>
                  </div>
                  <p className="text-[11px] text-gray-400 leading-snug mt-0.5">{s.detail}</p>
                </div>
              ))}
            </div>
          </section>

          {/* References */}
          <section className="pb-4">
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-2">References</h3>
            <ul className="space-y-1 text-xs text-gray-500">
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
