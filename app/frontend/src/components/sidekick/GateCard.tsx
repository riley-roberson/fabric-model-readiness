import { useState } from "react";
import type { GateStateEntry, ProcessGate, ProcessStep } from "@/types/sidekick";

interface GateCardProps {
  gate: ProcessGate;
  entry: GateStateEntry | undefined;
  stepsById: Map<string, ProcessStep>;
  busy: boolean;
  onAttest: (attestedBy: string, note: string) => void;
}

/**
 * A stakeholder gate. Unlike steps, this does not bend: while any prerequisite
 * is outstanding the form is not offered at all, and the outstanding items are
 * named so it is obvious what would unblock it.
 */
export function GateCard({ gate, entry, stepsById, busy, onAttest }: GateCardProps) {
  const [who, setWho] = useState("");
  const [note, setNote] = useState("");

  const passed = entry?.passed ?? false;
  const blocking = entry?.blocking ?? gate.requires;

  return (
    <div
      className={`
        rounded-lg border-2 p-5
        ${passed
          ? "border-emerald-500/40 bg-emerald-500/[0.06]"
          : blocking.length > 0
            ? "border-amber-500/40 bg-amber-500/[0.05]"
            : "border-blue-500/50 bg-blue-500/[0.06]"}
      `}
    >
      <div className="flex items-center gap-2 mb-2">
        <svg width="16" height="16" className={passed ? "text-emerald-400" : "text-amber-400"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          {passed ? (
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
          )}
        </svg>
        <span className="text-[10px] uppercase tracking-widest font-bold text-slate-400">
          Stakeholder gate
        </span>
      </div>

      <p className="text-sm font-bold text-slate-100">{gate.text}</p>

      {passed ? (
        <p className="mt-2 text-xs text-emerald-400">
          Signed off by {entry?.attested_by}
          {entry?.attested_at ? ` on ${entry.attested_at.slice(0, 10)}` : ""}
          {entry?.note ? ` — ${entry.note}` : ""}
        </p>
      ) : blocking.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs text-amber-400/90 font-medium mb-1.5">
            {blocking.length} step{blocking.length === 1 ? "" : "s"} outstanding:
          </p>
          <ul className="space-y-1">
            {blocking.map((id) => (
              <li key={id} className="text-xs text-slate-400 flex items-start gap-1.5">
                <span className="text-amber-500/60 mt-0.5">▸</span>
                <span>{stepsById.get(id)?.text ?? id}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-slate-400">
            Everything this gate requires is resolved. Record who accepted it.
          </p>
          <div className="flex items-center gap-2">
            <input
              value={who}
              onChange={(e) => setWho(e.target.value)}
              placeholder="Who signed off?"
              className="flex-1 text-xs bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
            />
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Note (optional)"
              className="flex-1 text-xs bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
            />
            <button
              disabled={!who.trim() || busy}
              onClick={() => { onAttest(who.trim(), note); setWho(""); setNote(""); }}
              className="text-xs px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40 shrink-0"
            >
              Record
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
