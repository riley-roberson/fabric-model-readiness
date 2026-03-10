import { Component, useState, useMemo } from "react";
import type { ReactNode } from "react";
import type {
  HistorySession,
  HistoryChange,
  DeferredItem,
  CategoryConfig,
} from "@/types/history";
import { CATEGORY_ORDER, getCategoryConfig } from "@/types/history";

// ---------------------------------------------------------------------------
// Error boundary -- catches render crashes so the user can still navigate
// ---------------------------------------------------------------------------

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: string | null;
}

class SessionErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(err: Error) {
    return { error: err.message };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card p-4 border-red-500/30">
          <p className="text-sm text-red-400 font-medium">Failed to render session</p>
          <p className="text-xs text-red-400/60 mt-1 font-mono">{this.state.error}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface HistorySessionCardProps {
  session: HistorySession;
  deferredItems: DeferredItem[];
}

// ---------------------------------------------------------------------------
// Filter types
// ---------------------------------------------------------------------------

type StatusFilter = "all" | "applied" | "manual" | "deferred" | "rejected";

// ---------------------------------------------------------------------------
// Helpers -- safe accessors
// ---------------------------------------------------------------------------

function safeByAction(session: HistorySession) {
  return session?.sessionSummary?.byAction ?? { accepted: 0, deferred: 0, rejected: 0 };
}

// ---------------------------------------------------------------------------
// Grouping logic
// ---------------------------------------------------------------------------

interface ChangeGroup {
  label: string;
  items: HistoryChange[];
}

interface CategoryGroup {
  category: string;
  config: CategoryConfig;
  accepted: number;
  deferred: number;
  rejected: number;
  groups: ChangeGroup[];
}

/** Extract a prefix pattern from a description for bulk grouping. */
function extractPattern(description: string): string {
  if (!description) return "unknown";

  const prefixes = [
    /^(Add column description)\b/i,
    /^(Add table description)\b/i,
    /^(Add measure description)\b/i,
    /^(Add description)\b/i,
    /^(Add synonyms?\b.*?columns?)\b/i,
    /^(Hide surrogate key)\b/i,
    /^(Set default summarization)\b/i,
    /^(Set Data Category)\b/i,
    /^(Configure Sort By Column)\b/i,
    /^(Rename ambiguous)\b/i,
    /^(Exclude .+ from AI schema)\b/i,
  ];

  for (const pat of prefixes) {
    const m = description.match(pat);
    if (m) return m[1];
  }

  // Fallback: take the description up to " for ", " to ", " on " -- common prepositions
  const cut = description.match(/^(.{15,}?)\s+(?:for|to|on|from)\s/i);
  if (cut) return cut[1];

  return description; // unique -- won't group
}

function groupChanges(changes: HistoryChange[]): CategoryGroup[] {
  if (!changes || changes.length === 0) return [];

  // 1. Group by category
  const byCat = new Map<string, HistoryChange[]>();
  for (const c of changes) {
    const cat = c.category || "unknown";
    const list = byCat.get(cat) || [];
    list.push(c);
    byCat.set(cat, list);
  }

  // 2. Build CategoryGroup array in display order
  const ordered = [...CATEGORY_ORDER];
  for (const cat of byCat.keys()) {
    if (!ordered.includes(cat)) ordered.push(cat);
  }

  const result: CategoryGroup[] = [];

  for (const cat of ordered) {
    const items = byCat.get(cat);
    if (!items || items.length === 0) continue;

    const config = getCategoryConfig(cat);
    const accepted = items.filter((c) => c.action === "accepted").length;
    const deferred = items.filter((c) => c.action === "deferred").length;
    const rejected = items.filter((c) => c.action === "rejected").length;

    // Sub-group by description pattern
    const byPattern = new Map<string, HistoryChange[]>();
    for (const item of items) {
      const pattern = extractPattern(item.description);
      const list = byPattern.get(pattern) || [];
      list.push(item);
      byPattern.set(pattern, list);
    }

    const groups: ChangeGroup[] = [];
    for (const [pattern, patternItems] of byPattern) {
      if (patternItems.length > 3) {
        const label = deriveBulkLabel(pattern, patternItems.length);
        groups.push({ label, items: patternItems });
      } else {
        for (const item of patternItems) {
          groups.push({ label: item.description, items: [item] });
        }
      }
    }

    result.push({ category: cat, config, accepted, deferred, rejected, groups });
  }

  return result;
}

function deriveBulkLabel(pattern: string, count: number): string {
  const cleaned = pattern
    .replace(/^Add\s+/i, "")
    .replace(/^Set\s+/i, "")
    .replace(/^Configure\s+/i, "")
    .replace(/^Hide\s+/i, "Hidden ");

  const label = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  return `${label} (${count})`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusCard({
  label,
  count,
  colorClass,
  borderClass,
}: {
  label: string;
  count: number;
  colorClass: string;
  borderClass: string;
}) {
  return (
    <div className={`rounded-lg border px-3 py-2 text-center ${borderClass}`}>
      <p className={`text-lg font-bold ${colorClass}`}>{count}</p>
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
    </div>
  );
}

function ActionBadge({ action }: { action: string }) {
  const cls =
    action === "accepted"
      ? "bg-emerald-500/20 text-emerald-400"
      : action === "deferred"
        ? "bg-amber-500/20 text-amber-400"
        : action === "rejected"
          ? "bg-red-500/20 text-red-400"
          : "bg-slate-500/20 text-slate-400";
  return (
    <span className={`px-1.5 py-0.5 rounded font-bold text-[10px] uppercase ${cls}`}>
      {action}
    </span>
  );
}

function BulkGroup({ group }: { group: ChangeGroup }) {
  const [expanded, setExpanded] = useState(false);
  const isBulk = group.items.length > 1;

  if (!isBulk) {
    const item = group.items[0];
    if (!item) return null;
    return <IndividualChange change={item} />;
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-800/30">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-800/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <svg
          width="12"
          height="12"
          className={`text-slate-500 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <span className="text-xs font-medium text-slate-300">{group.label}</span>
        <span className="ml-auto">
          <ActionBadge action={group.items[0]?.action ?? "unknown"} />
        </span>
      </button>
      {expanded && (
        <div className="border-t border-slate-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 text-left">
                <th className="px-3 py-1.5 font-medium w-20">Finding</th>
                <th className="px-3 py-1.5 font-medium">Object</th>
                <th className="px-3 py-1.5 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {group.items.map((item, idx) => (
                <tr key={item.findingId ?? idx} className="border-t border-slate-800/50">
                  <td className="px-3 py-1.5 text-slate-500 font-mono">{item.findingId}</td>
                  <td className="px-3 py-1.5 text-slate-300">{item.object}</td>
                  <td className="px-3 py-1.5 text-slate-500 truncate max-w-[300px]">
                    {item.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function IndividualChange({ change }: { change: HistoryChange }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetail = change.before != null || change.after != null || change.reason;

  return (
    <div className="flex items-start gap-2 text-xs py-2 px-3 rounded-lg bg-slate-800/50">
      <ActionBadge action={change.action} />
      <div className="flex-1 min-w-0">
        <span className="text-slate-300 font-medium">{change.object}</span>
        <span className="text-slate-500 ml-2">{change.description}</span>
        {change.reason && (
          <span className="text-amber-400/70 ml-2 italic">-- {change.reason}</span>
        )}
        {hasDetail && (
          <button
            className="ml-2 text-blue-400/60 hover:text-blue-400 text-[10px]"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "hide" : "detail"}
          </button>
        )}
        {expanded && (
          <div className="mt-1.5 text-[11px] space-y-1">
            {change.before != null && (
              <p className="text-red-400/60">
                <span className="font-medium">Before:</span> {String(change.before)}
              </p>
            )}
            {change.after != null && (
              <p className="text-emerald-400/60">
                <span className="font-medium">After:</span> {String(change.after)}
              </p>
            )}
          </div>
        )}
      </div>
      <span className="text-slate-600 font-mono text-[10px] shrink-0">{change.findingId}</span>
    </div>
  );
}

function CategorySection({ group }: { group: CategoryGroup }) {
  const [collapsed, setCollapsed] = useState(false);
  const total = group.accepted + group.deferred + group.rejected;
  const cfg = group.config;

  const pctA = total > 0 ? (group.accepted / total) * 100 : 0;
  const pctD = total > 0 ? (group.deferred / total) * 100 : 0;
  const pctR = total > 0 ? (group.rejected / total) * 100 : 0;

  return (
    <div className="mb-3">
      <button
        className={`w-full flex items-center gap-2 pb-1.5 mb-2 border-b ${cfg.borderClass} text-left`}
        onClick={() => setCollapsed(!collapsed)}
      >
        <svg
          width="10"
          height="10"
          className={`text-slate-500 transition-transform ${collapsed ? "" : "rotate-90"}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <div className={`w-2 h-2 rounded-full ${cfg.dotClass}`} />
        <h3 className={`text-xs font-bold uppercase tracking-widest ${cfg.textClass}`}>
          {cfg.label}
        </h3>
        <span className="text-xs text-slate-600">({total})</span>
        <div className="ml-auto flex items-center gap-2">
          <div className="w-24 h-1.5 rounded-full bg-slate-800 overflow-hidden flex">
            {pctA > 0 && <div className="h-full bg-emerald-500" style={{ width: `${pctA}%` }} />}
            {pctD > 0 && <div className="h-full bg-amber-500" style={{ width: `${pctD}%` }} />}
            {pctR > 0 && <div className="h-full bg-red-500" style={{ width: `${pctR}%` }} />}
          </div>
        </div>
      </button>
      {!collapsed && (
        <div className="space-y-1">
          {group.groups.map((g, i) => (
            <BulkGroup key={i} group={g} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component (wrapped with error boundary)
// ---------------------------------------------------------------------------

export function HistorySessionCard({ session, deferredItems }: HistorySessionCardProps) {
  return (
    <SessionErrorBoundary>
      <HistorySessionCardInner session={session} deferredItems={deferredItems ?? []} />
    </SessionErrorBoundary>
  );
}

function HistorySessionCardInner({ session, deferredItems }: HistorySessionCardProps) {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");

  const byAction = safeByAction(session);
  const changes = session?.changes ?? [];

  // Determine applied/manual counts from appliedSummary
  const applied = session?.appliedSummary?.appliedViaMCP ?? byAction.accepted;
  const manual = session?.appliedSummary?.skippedMCPUnsupported ?? 0;
  const deferred = byAction.deferred;
  const rejected = byAction.rejected;

  // Filter changes
  const filteredChanges = useMemo(() => {
    let result = changes;

    if (filter === "applied") {
      result = result.filter((c) => c.action === "accepted");
    } else if (filter === "manual") {
      const manualIds = new Set(
        session?.appliedSummary?.notes?.match(/f-\d+/g) ?? []
      );
      result = result.filter((c) => c.action === "accepted" && manualIds.has(c.findingId));
    } else if (filter === "deferred") {
      result = result.filter((c) => c.action === "deferred");
    } else if (filter === "rejected") {
      result = result.filter((c) => c.action === "rejected");
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (c) =>
          (c.object ?? "").toLowerCase().includes(q) ||
          (c.description ?? "").toLowerCase().includes(q) ||
          (c.findingId ?? "").toLowerCase().includes(q)
      );
    }

    return result;
  }, [changes, session?.appliedSummary, filter, search]);

  const categoryGroups = useMemo(() => groupChanges(filteredChanges), [filteredChanges]);

  const scoreColor =
    (session?.preScore ?? 0) >= 90
      ? "text-emerald-400"
      : (session?.preScore ?? 0) >= 75
        ? "text-blue-400"
        : (session?.preScore ?? 0) >= 50
          ? "text-amber-400"
          : "text-red-400";

  const filterButtons: { key: StatusFilter; label: string; count: number }[] = [
    { key: "all", label: "All", count: changes.length },
    { key: "applied", label: "Applied", count: applied },
    ...(manual > 0 ? [{ key: "manual" as StatusFilter, label: "Manual Required", count: manual }] : []),
    ...(deferred > 0 ? [{ key: "deferred" as StatusFilter, label: "Deferred", count: deferred }] : []),
    ...(rejected > 0 ? [{ key: "rejected" as StatusFilter, label: "Rejected", count: rejected }] : []),
  ];

  return (
    <div className="space-y-3">
      {/* Session Header */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm text-slate-500">
              {session?.timestamp
                ? new Date(session.timestamp).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })
                : "Unknown date"}
              {session?.appliedTimestamp && (
                <span className="ml-2 text-slate-600">
                  (applied{" "}
                  {new Date(session.appliedTimestamp).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                  )
                </span>
              )}
            </p>
            <p className="text-[10px] text-slate-600 font-mono mt-0.5">
              {(session?.sessionId ?? "").slice(0, 8)}
            </p>
          </div>
          <div className="text-right">
            <span className={`text-xl font-bold ${scoreColor}`}>{session?.preScore ?? "?"}</span>
            {session?.postScore != null ? (
              <span className="text-blue-400 text-sm ml-1">
                &rarr; {session.postScore}
              </span>
            ) : (
              <span className="text-slate-600 text-xs ml-1">/ 100</span>
            )}
          </div>
        </div>

        {/* Status cards grid */}
        <div className="grid grid-cols-4 gap-2">
          <StatusCard
            label="Applied"
            count={applied}
            colorClass="text-emerald-400"
            borderClass="border-emerald-500/20 bg-emerald-500/5"
          />
          <StatusCard
            label="Manual"
            count={manual}
            colorClass="text-blue-400"
            borderClass="border-blue-500/20 bg-blue-500/5"
          />
          <StatusCard
            label="Deferred"
            count={deferred}
            colorClass="text-amber-400"
            borderClass="border-amber-500/20 bg-amber-500/5"
          />
          <StatusCard
            label="Rejected"
            count={rejected}
            colorClass="text-red-400"
            borderClass="border-red-500/20 bg-red-500/5"
          />
        </div>
      </div>

      {/* Action-Required Banner */}
      {manual > 0 && (
        <ManualRequiredBanner session={session} count={manual} />
      )}

      {/* Filter Bar */}
      <div className="card px-3 py-2 flex items-center gap-2 flex-wrap">
        {filterButtons.map((btn) => (
          <button
            key={btn.key}
            className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
              filter === btn.key
                ? "bg-blue-600/10 border-blue-500/40 text-blue-400"
                : "border-slate-700 text-slate-500 hover:text-slate-300 hover:border-slate-600"
            }`}
            onClick={() => setFilter(btn.key)}
          >
            {btn.label}
            <span className="ml-1 text-slate-600">{btn.count}</span>
          </button>
        ))}
        <div className="flex-1" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search objects..."
          className="text-xs bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-300 placeholder:text-slate-600 w-44 focus:outline-none focus:border-blue-500/40"
        />
      </div>

      {/* Category Sections */}
      {categoryGroups.length > 0 ? (
        <div>
          {categoryGroups.map((group) => (
            <CategorySection key={group.category} group={group} />
          ))}
        </div>
      ) : (
        <div className="card p-4 text-center">
          <p className="text-sm text-slate-500">No changes match the current filter.</p>
        </div>
      )}

      {/* Deferred Items Section */}
      {deferredItems.length > 0 && (
        <div className="card p-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-amber-400 mb-2">
            Outstanding Deferred Items
          </h3>
          <div className="space-y-1">
            {deferredItems.map((item) => (
              <div
                key={item.findingId}
                className="flex items-center gap-2 text-xs py-1.5 px-3 rounded-lg bg-amber-500/5 border border-amber-500/10"
              >
                <span className="text-slate-500 font-mono text-[10px] w-12 shrink-0">
                  {item.findingId}
                </span>
                <span className="text-slate-300">{item.object}</span>
                <span className="text-amber-400/60 truncate">{item.reason ?? item.description}</span>
                <span className="ml-auto text-slate-600 text-[10px] shrink-0">
                  {item.sessionDate
                    ? new Date(item.sessionDate).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                      })
                    : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Manual-required banner
// ---------------------------------------------------------------------------

function ManualRequiredBanner({
  session,
  count,
}: {
  session: HistorySession;
  count: number;
}) {
  const [expanded, setExpanded] = useState(false);

  const manualIds = new Set(
    session?.appliedSummary?.notes?.match(/f-\d+/g) ?? []
  );
  const manualChanges = (session?.changes ?? []).filter(
    (c) => c.action === "accepted" && manualIds.has(c.findingId)
  );

  return (
    <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 px-4 py-3">
      <button
        className="w-full flex items-center gap-2 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <svg width="14" height="14" className="text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
        </svg>
        <span className="text-xs font-medium text-blue-400">
          {count} changes require manual action in Power BI Desktop
        </span>
        <svg
          width="10"
          height="10"
          className={`text-blue-400/60 ml-auto transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
      </button>
      {expanded && manualChanges.length > 0 && (
        <div className="mt-2 space-y-1">
          {manualChanges.map((c) => (
            <div key={c.findingId} className="flex items-center gap-2 text-xs py-1 text-blue-300/80">
              <span className="font-mono text-[10px] text-blue-400/60">{c.findingId}</span>
              <span>{c.description}</span>
            </div>
          ))}
        </div>
      )}
      {expanded && session?.appliedSummary?.notes && (
        <p className="mt-2 text-[11px] text-blue-300/50 italic">{session.appliedSummary.notes}</p>
      )}
    </div>
  );
}
