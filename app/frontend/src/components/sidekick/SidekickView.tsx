import { useMemo, useState } from "react";
import { useSidekick } from "@/hooks/useSidekick";
import type { ProcessStep } from "@/types/sidekick";
import { GateCard } from "./GateCard";
import { StepCard } from "./StepCard";

interface SidekickViewProps {
  /** Offered as the project root when no project is open yet. */
  suggestedPath?: string;
  onPickFolder: () => Promise<string | null>;
}

export function SidekickView({ suggestedPath, onPickFolder }: SidekickViewProps) {
  const sk = useSidekick();
  const [expanded, setExpanded] = useState<string | null>(null);

  const stepsById = useMemo(() => {
    const map = new Map<string, ProcessStep>();
    for (const stage of sk.process?.stages ?? []) {
      for (const step of stage.steps) map.set(step.id, step);
    }
    return map;
  }, [sk.process]);

  if (!sk.process) {
    return <p className="text-sm text-slate-500 text-center py-12">Loading the process…</p>;
  }

  // -- no project open yet --------------------------------------------------
  if (!sk.state) {
    return (
      <div className="max-w-md mx-auto card p-8 text-center">
        <h2 className="text-lg font-bold text-slate-100 mb-2">Semantic Model Sidekick</h2>
        <p className="text-sm text-slate-400 mb-1">
          Walks a project through the {sk.process.total_steps}-step development process, showing only
          what matters at your current stage.
        </p>
        <p className="text-xs text-slate-600 mb-6">
          {sk.process.source_document} · revision {sk.process.doc_revision}
        </p>
        <button
          className="btn-primary text-sm px-4 py-2"
          disabled={sk.busy}
          onClick={async () => {
            const path = await onPickFolder();
            if (path) await sk.openProject(path);
          }}
        >
          Choose the project folder
        </button>
        {suggestedPath && (
          <p className="mt-3 text-[11px] text-slate-600 break-all">Suggested: {suggestedPath}</p>
        )}
        {sk.error && <p className="mt-4 text-xs text-red-400">{sk.error}</p>}
      </div>
    );
  }

  const { state, findings } = sk;
  const currentStage = sk.process.stages.find((s) => s.id === state.current_stage);

  return (
    <div className="max-w-3xl mx-auto pb-6">
      {/* Where you are, always visible */}
      <div className="card p-5 mb-4">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="min-w-0">
            <h2 className="text-base font-bold text-slate-100 truncate">{state.name}</h2>
            <p className="text-xs text-slate-500">
              Stage {state.current_stage_index} of {state.stage_count} ·{" "}
              {state.completion.resolved} of {state.completion.total} steps · {state.size} project
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-2xl font-black text-blue-400 tabular-nums">
              {state.completion.percent}%
            </p>
            <p className="text-[10px] uppercase tracking-wider text-slate-600 font-bold">complete</p>
          </div>
        </div>

        <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${state.completion.percent}%` }}
          />
        </div>

        {state.next_step && (
          <p className="mt-3 text-xs text-slate-400">
            <span className="text-slate-600">Next:</span>{" "}
            <span className="text-slate-200">
              Step {state.next_step.index} — {state.next_step.text}
            </span>
          </p>
        )}

        {/* The point of phase-aware linting, stated plainly */}
        {findings && findings.progress.checks_in_play > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between gap-3">
            <p className="text-xs text-slate-400">
              <span className="font-bold text-slate-200">{findings.progress.percent}%</span> of what
              should be true at this stage
              <span className="text-slate-600">
                {" "}· {findings.progress.checks_in_play} checks in play
              </span>
            </p>
            {findings.progress.suppressed > 0 && (
              <p className="text-[11px] text-slate-600 shrink-0">
                {findings.progress.suppressed} not relevant yet
              </p>
            )}
          </div>
        )}
      </div>

      {sk.error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start justify-between gap-3">
          <p className="text-xs text-red-300">{sk.error}</p>
          <button onClick={sk.clearError} className="text-xs text-red-400 hover:text-red-200 shrink-0">
            Dismiss
          </button>
        </div>
      )}

      {/* The spine */}
      <div className="space-y-2">
        {sk.process.stages.map((stage) => {
          const isCurrent = stage.id === state.current_stage;
          const isOpen = expanded === stage.id || (expanded === null && isCurrent);
          const stageSteps = stage.steps.filter(
            (s) => !(s.optional_when === "size == small" && state.size === "small")
          );
          const resolved = stageSteps.filter(
            (s) => state.steps[s.id]?.state === "done" || state.steps[s.id]?.state === "skipped"
          ).length;

          return (
            <div key={stage.id} className="card overflow-hidden">
              <button
                onClick={() => setExpanded(isOpen ? "" : stage.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors
                  ${isCurrent ? "bg-blue-500/[0.06]" : "hover:bg-slate-800/40"}`}
              >
                <span
                  className={`shrink-0 w-6 h-6 rounded flex items-center justify-center text-[11px] font-bold tabular-nums
                    ${resolved === stageSteps.length && stageSteps.length > 0
                      ? "bg-emerald-500/20 text-emerald-400"
                      : isCurrent ? "bg-blue-500/20 text-blue-400" : "bg-slate-800 text-slate-500"}`}
                >
                  {sk.process!.stages.indexOf(stage) + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className={`block text-sm font-semibold truncate ${isCurrent ? "text-blue-300" : "text-slate-300"}`}>
                    {stage.title}
                  </span>
                  <span className="block text-[11px] text-slate-600">
                    {resolved}/{stageSteps.length} steps
                    {stage.proposed && " · proposed stage"}
                  </span>
                </span>
                {!isCurrent && (
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => { e.stopPropagation(); void sk.setStage(stage.id); }}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.stopPropagation(); void sk.setStage(stage.id); } }}
                    className="text-[11px] px-2 py-1 rounded text-slate-500 hover:text-blue-400 hover:bg-slate-800 shrink-0"
                  >
                    Work here
                  </span>
                )}
                <svg width="14" height="14" className={`text-slate-600 shrink-0 transition-transform ${isOpen ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>

              {isOpen && (
                <div className="px-4 pb-4 space-y-2">
                  {/* An unratified stage must say so before its steps are read */}
                  {stage.proposed && stage.proposal_note && (
                    <div className="rounded-md border border-amber-500/25 bg-amber-500/[0.06] p-3">
                      <p className="text-[10px] uppercase tracking-wider font-bold text-amber-400 mb-1">
                        Proposed, not yet org process
                      </p>
                      <p className="text-xs text-amber-200/80 leading-relaxed">{stage.proposal_note}</p>
                    </div>
                  )}

                  {/* Advice that belongs here even though it is checked later */}
                  {stage.heads_up && (
                    <div className="rounded-md border border-blue-500/25 bg-blue-500/[0.05] p-3">
                      <p className="text-[10px] uppercase tracking-wider font-bold text-blue-400 mb-1">
                        Worth doing now
                      </p>
                      <p className="text-xs text-blue-200/80 leading-relaxed">{stage.heads_up}</p>
                    </div>
                  )}

                  {stageSteps.map((step) => (
                    <StepCard
                      key={step.id}
                      step={step}
                      entry={state.steps[step.id]}
                      isNext={state.next_step?.id === step.id}
                      busy={sk.busy}
                      onMark={(status, opts) => void sk.markStep(step.id, status, opts)}
                    />
                  ))}

                  {stage.gate && (
                    <GateCard
                      gate={stage.gate}
                      entry={state.gates[stage.gate.id]}
                      stepsById={stepsById}
                      busy={sk.busy}
                      onAttest={(who, note) => void sk.attestGate(stage.gate!.id, who, note)}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {currentStage && findings && findings.findings.length > 0 && (
        <div className="card p-4 mt-4">
          <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
            Worth fixing at this stage · {findings.findings.length}
          </p>
          <ul className="space-y-1.5 max-h-64 overflow-y-auto">
            {findings.findings.slice(0, 40).map((f) => (
              <li key={f.id} className="text-xs bg-slate-900/60 rounded p-2 border border-slate-800">
                <span className="text-slate-300 font-medium">{f.object}</span>
                <span className="text-slate-600"> · {f.check}</span>
                <p className="text-slate-500 mt-0.5">{f.message}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
