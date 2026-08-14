import { useCallback, useEffect, useState } from "react";

interface Location {
  what: string;
  surface: string;
  path: string;
  doc_url: string;
  note: string;
}

interface Suggestion {
  id: string;
  title: string;
  body: string;
  severity: "blocker" | "important" | "advisory";
  location: Location | null;
  check: string;
}

interface ChecklistItem {
  id: string;
  text: string;
  emphasis?: string;
  why?: string;
  check?: string;
  example?: string;
  doc_url?: string;
}

interface Advice {
  model_name: string;
  readiness_score: number;
  readiness_threshold: number;
  critical_findings: number;
  agent_known: boolean;
  table_selection: { tables: string[]; count: number; source: string; complete: boolean };
  suggestions: Suggestion[];
  test_questions: { text: string; origin: string; expects: string }[];
  checklist: { sections: { id: string; title: string; items: ChecklistItem[] }[] };
}

interface DataAgentViewProps {
  modelPath: string;
  onPickModel: () => Promise<string | null>;
}

function backendUrl(): string {
  const port = new URLSearchParams(window.location.search).get("port") || "8000";
  return `http://127.0.0.1:${port}`;
}

const SEVERITY_STYLE: Record<string, { border: string; text: string; label: string }> = {
  blocker: { border: "border-red-500/40 bg-red-500/[0.05]", text: "text-red-400", label: "Blocker" },
  important: { border: "border-amber-500/40 bg-amber-500/[0.04]", text: "text-amber-400", label: "Important" },
  advisory: { border: "border-slate-700 bg-slate-900/40", text: "text-slate-400", label: "Advisory" },
};

const SURFACE_LABEL: Record<string, string> = {
  "fabric-portal": "Fabric portal",
  "power-bi-desktop": "Power BI Desktop",
  "power-bi-service": "Power BI service",
  sdk: "Python SDK",
};

/** Where to go, rendered so it can be followed without leaving the app. */
function WhereToGo({ location }: { location: Location }) {
  return (
    <div className="mt-3 rounded-md border border-slate-700/60 bg-slate-950/50 p-2.5">
      <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">
        {SURFACE_LABEL[location.surface] ?? location.surface}
      </p>
      <p className="text-xs text-slate-300 font-mono leading-relaxed break-words">{location.path}</p>
      {location.note && <p className="mt-1.5 text-[11px] text-slate-500">{location.note}</p>}
      {location.doc_url && (
        <a
          href={location.doc_url}
          target="_blank"
          rel="noreferrer"
          className="mt-1.5 inline-block text-[11px] text-blue-400 hover:text-blue-300"
        >
          Documentation →
        </a>
      )}
    </div>
  );
}

export function DataAgentView({ modelPath, onPickModel }: DataAgentViewProps) {
  const [path, setPath] = useState(modelPath);
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showTests, setShowTests] = useState(false);

  // Pasted-in agent config. Deliberately optional: the two most important
  // checks work from this text alone, with no Fabric connection.
  const [agentInstructions, setAgentInstructions] = useState("");
  const [agentTables, setAgentTables] = useState("");

  const load = useCallback(
    async (modelPathToUse: string, withConfig: boolean) => {
      if (!modelPathToUse) return;
      setBusy(true);
      setError(null);
      try {
        const res = withConfig
          ? await fetch(`${backendUrl()}/api/dataagent/advise`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                model_path: modelPathToUse,
                instructions: agentInstructions,
                data_sources: agentTables.trim()
                  ? [
                      {
                        name: advice?.model_name ?? "",
                        kind: "semantic_model",
                        selected_tables: agentTables.split("\n").map((t) => t.trim()).filter(Boolean),
                      },
                    ]
                  : [],
              }),
            })
          : await fetch(
              `${backendUrl()}/api/dataagent/advise?model_path=${encodeURIComponent(modelPathToUse)}`
            );
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || "Could not analyse");
        }
        setAdvice(await res.json());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not analyse");
      } finally {
        setBusy(false);
      }
    },
    [agentInstructions, agentTables, advice?.model_name]
  );

  useEffect(() => {
    if (modelPath) {
      setPath(modelPath);
      void load(modelPath, false);
    }
    // Only on the incoming model path changing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelPath]);

  const loadDraft = async () => {
    const res = await fetch(
      `${backendUrl()}/api/dataagent/instructions?model_path=${encodeURIComponent(path)}`
    );
    if (res.ok) setDraft((await res.json()).instructions);
  };

  if (!path) {
    return (
      <div className="max-w-md mx-auto card p-8 text-center">
        <h2 className="text-lg font-bold text-slate-100 mb-2">Data Agent Developer</h2>
        <p className="text-sm text-slate-400 mb-6">
          What to configure on the Fabric data agent, and where to find it. Everything here is
          derived from the semantic model, so most of it needs no Fabric connection.
        </p>
        <button
          className="btn-primary text-sm px-4 py-2"
          onClick={async () => {
            const picked = await onPickModel();
            if (picked) {
              setPath(picked);
              void load(picked, false);
            }
          }}
        >
          Choose a .SemanticModel folder
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto pb-6">
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {advice && (
        <>
          <div className="card p-5 mb-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="text-base font-bold text-slate-100 truncate">{advice.model_name}</h2>
                <p className="text-xs text-slate-500">
                  {advice.agent_known
                    ? "Checked against the agent configuration you provided"
                    : "No agent configuration provided — showing what to set up"}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p
                  className={`text-2xl font-black tabular-nums ${
                    advice.readiness_score < advice.readiness_threshold ? "text-red-400" : "text-emerald-400"
                  }`}
                >
                  {advice.readiness_score}
                </p>
                <p className="text-[10px] uppercase tracking-wider text-slate-600 font-bold">
                  model readiness
                </p>
              </div>
            </div>
          </div>

          {/* The list to tick off in the agent's Explorer */}
          {advice.table_selection.complete && (
            <div className="card p-4 mb-4">
              <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                Select exactly these {advice.table_selection.count} tables
              </p>
              <p className="text-[11px] text-slate-600 mb-2">{advice.table_selection.source}</p>
              <ul className="grid grid-cols-2 gap-1">
                {advice.table_selection.tables.map((t) => (
                  <li key={t} className="text-xs text-slate-300 flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm border border-slate-600 shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-3 mb-4">
            {advice.suggestions.map((s) => {
              const style = SEVERITY_STYLE[s.severity] ?? SEVERITY_STYLE.advisory;
              return (
                <div key={s.id} className={`rounded-lg border p-4 ${style.border}`}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-[10px] uppercase tracking-widest font-bold ${style.text}`}>
                      {style.label}
                    </span>
                    {s.check && <span className="text-[10px] text-slate-600 font-mono">{s.check}</span>}
                  </div>
                  <p className="text-sm font-semibold text-slate-100">{s.title}</p>
                  <p className="mt-1 text-xs text-slate-400 leading-relaxed whitespace-pre-line">{s.body}</p>
                  {s.location && <WhereToGo location={s.location} />}
                  {s.id === "draft_instructions" && (
                    <button
                      onClick={loadDraft}
                      className="mt-3 text-xs px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-medium"
                    >
                      Generate draft
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {draft && (
            <div className="card p-4 mb-4">
              <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Draft agent instructions
              </p>
              <pre className="text-[11px] text-slate-300 bg-slate-950 rounded p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {draft}
              </pre>
            </div>
          )}

          {/* No Fabric connection needed: both very-important rules are
              checkable from pasted text alone. */}
          <div className="card p-4 mb-4">
            <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
              Check an existing agent
            </p>
            <p className="text-[11px] text-slate-500 mb-3">
              Paste what the agent has today. No Fabric connection required — the two rules that
              matter most are checkable from this alone.
            </p>
            <textarea
              value={agentInstructions}
              onChange={(e) => setAgentInstructions(e.target.value)}
              placeholder="Paste the agent's instructions..."
              rows={4}
              className="w-full text-xs bg-slate-950 border border-slate-700 rounded p-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 mb-2"
            />
            <textarea
              value={agentTables}
              onChange={(e) => setAgentTables(e.target.value)}
              placeholder="Tables selected in the agent, one per line..."
              rows={3}
              className="w-full text-xs bg-slate-950 border border-slate-700 rounded p-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 mb-2"
            />
            <button
              disabled={busy || (!agentInstructions.trim() && !agentTables.trim())}
              onClick={() => void load(path, true)}
              className="text-xs px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40"
            >
              {busy ? "Checking..." : "Check it"}
            </button>
          </div>

          {advice.test_questions.length > 0 && (
            <div className="card p-4 mb-4">
              <button
                onClick={() => setShowTests(!showTests)}
                className="w-full flex items-center justify-between text-left"
              >
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  {advice.test_questions.length} generated test questions
                </span>
                <span className="text-slate-600 text-xs">{showTests ? "hide" : "show"}</span>
              </button>
              {showTests && (
                <ul className="mt-3 space-y-1.5">
                  {advice.test_questions.map((q, i) => (
                    <li key={i} className="text-xs bg-slate-900/60 rounded p-2 border border-slate-800">
                      <p className="text-slate-200">{q.text}</p>
                      <p className="text-[10px] text-slate-600 mt-0.5">
                        from {q.origin.replace("_", " ")}
                        {q.expects ? ` · expects ${q.expects}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* The 18 checklist items the Analyzer deliberately does not score */}
          {advice.checklist.sections.map((section) => (
            <div key={section.id} className="card p-4 mb-3">
              <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                {section.title}
              </p>
              <ul className="space-y-2">
                {section.items.map((item) => (
                  <li key={item.id} className="text-xs border-l-2 border-slate-800 pl-2.5">
                    <div className="flex items-start gap-1.5">
                      {item.emphasis === "warning" && (
                        <span className="text-[9px] uppercase font-bold text-red-400 bg-red-500/10 rounded px-1 shrink-0">
                          Do not
                        </span>
                      )}
                      {item.emphasis === "important" && (
                        <span className="text-[9px] uppercase font-bold text-amber-400 bg-amber-500/10 rounded px-1 shrink-0">
                          Important
                        </span>
                      )}
                      <span className="text-slate-300">{item.text}</span>
                    </div>
                    {item.why && <p className="text-slate-500 mt-0.5">{item.why}</p>}
                    {item.check && (
                      <p className="text-[10px] text-emerald-500/70 mt-0.5 font-mono">
                        checked automatically · {item.check}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
