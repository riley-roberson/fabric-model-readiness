import { useState } from "react";
import type { ProcessStep, StepStateEntry } from "@/types/sidekick";

interface StepCardProps {
  step: ProcessStep;
  entry: StepStateEntry | undefined;
  isNext: boolean;
  busy: boolean;
  onMark: (status: "done" | "skipped" | "pending", opts?: { note?: string; reason?: string }) => void;
}

/** What kind of proof this step needs, in the user's language. */
const EVIDENCE_LABEL: Record<string, string> = {
  manual: "You confirm",
  artifact: "Needs a document",
  lint: "Checked automatically",
  naming: "Checked automatically",
  derived: "Checked automatically",
  external: "Done in the Service",
};

export function StepCard({ step, entry, isNext, busy, onMark }: StepCardProps) {
  const [skipping, setSkipping] = useState(false);
  const [reason, setReason] = useState("");

  const status = entry?.state ?? "pending";
  const done = status === "done";
  const skipped = status === "skipped";

  const border = done
    ? "border-emerald-500/30 bg-emerald-500/[0.04]"
    : skipped
      ? "border-slate-700 bg-slate-900/40"
      : isNext
        ? "border-blue-500/50 bg-blue-500/[0.04]"
        : "border-slate-800 bg-slate-900/40";

  return (
    <div className={`rounded-lg border p-4 transition-colors ${border}`}>
      <div className="flex items-start gap-3">
        {/* Step number, the way an instruction book numbers them */}
        <div
          className={`
            shrink-0 w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold tabular-nums
            ${done ? "bg-emerald-500/20 text-emerald-400"
              : skipped ? "bg-slate-800 text-slate-600"
              : isNext ? "bg-blue-500/20 text-blue-400"
              : "bg-slate-800 text-slate-500"}
          `}
        >
          {done ? "✓" : skipped ? "–" : step.index}
        </div>

        <div className="min-w-0 flex-1">
          <p className={`text-sm font-medium ${skipped ? "text-slate-500 line-through" : "text-slate-100"}`}>
            {step.text}
          </p>
          {step.detail && <p className="mt-1 text-xs text-slate-400 leading-relaxed">{step.detail}</p>}

          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500 bg-slate-800/80 rounded px-1.5 py-0.5">
              {EVIDENCE_LABEL[step.evidence] ?? step.evidence}
            </span>
            {step.proposed && (
              <span
                className="text-[10px] uppercase tracking-wider font-bold text-amber-400 bg-amber-500/10 border border-amber-500/25 rounded px-1.5 py-0.5"
                title="Not in the process document. Awaiting the document owner's ratification."
              >
                Proposed
              </span>
            )}
            {step.checks.length > 0 && (
              <span className="text-[10px] text-slate-500">{step.checks.length} linter checks</span>
            )}
          </div>

          {/* The parts callout: what you need in hand before starting */}
          {step.artifacts.length > 0 && (
            <div className="mt-3 rounded-md border border-slate-700/60 bg-slate-950/40 p-2.5">
              <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1.5">
                You'll need
              </p>
              <ul className="space-y-1">
                {step.artifacts.map((a) => (
                  <li key={a} className="text-xs text-slate-400 flex items-start gap-1.5">
                    <span className="text-slate-600 mt-0.5">▸</span>
                    <span className="break-all">{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {skipped && entry?.reason && (
            <p className="mt-2 text-xs text-slate-500 italic">Skipped: {entry.reason}</p>
          )}
          {done && entry?.note && <p className="mt-2 text-xs text-slate-400">{entry.note}</p>}

          {skipping ? (
            <div className="mt-3 flex items-center gap-2">
              <input
                autoFocus
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why is this step not needed?"
                className="flex-1 text-xs bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
              />
              <button
                disabled={!reason.trim() || busy}
                onClick={() => {
                  onMark("skipped", { reason });
                  setSkipping(false);
                  setReason("");
                }}
                className="text-xs px-2.5 py-1.5 rounded bg-slate-700 text-slate-200 disabled:opacity-40 hover:bg-slate-600"
              >
                Skip
              </button>
              <button
                onClick={() => { setSkipping(false); setReason(""); }}
                className="text-xs px-2 py-1.5 text-slate-500 hover:text-slate-300"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="mt-3 flex items-center gap-2">
              {status === "pending" ? (
                <>
                  <button
                    disabled={busy}
                    onClick={() => onMark("done")}
                    className="text-xs px-3 py-1.5 rounded bg-emerald-600/90 hover:bg-emerald-500 text-white font-medium disabled:opacity-40"
                  >
                    Mark done
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => setSkipping(true)}
                    className="text-xs px-2.5 py-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-40"
                  >
                    Not needed
                  </button>
                </>
              ) : (
                <button
                  disabled={busy}
                  onClick={() => onMark("pending")}
                  className="text-xs px-2.5 py-1.5 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                >
                  Reopen
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
