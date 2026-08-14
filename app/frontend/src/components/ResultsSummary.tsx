import type { ApplyResult } from "@/types/scan";

interface ResultsSummaryProps {
  result: ApplyResult;
  preScore: number;
  onViewHistory: () => void;
  onNewScan: () => void;
}

export function ResultsSummary({ result, preScore, onViewHistory, onNewScan }: ResultsSummaryProps) {
  const rolledBack = result.rolled_back;
  const partial = !rolledBack && (result.failed.length > 0 || result.unsupported.length > 0);

  const heading = rolledBack
    ? "Rolled Back"
    : result.applied === 0
      ? "Nothing Applied"
      : partial
        ? "Partially Applied"
        : "Changes Applied";

  const tone = rolledBack
    ? { bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400" }
    : partial
      ? { bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400" }
      : { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400" };

  return (
    <div className="flex flex-col items-center justify-center h-full py-6">
      <div className="w-full max-w-md card p-8 text-center">
        <div className={`mx-auto w-10 h-10 rounded-lg ${tone.bg} border ${tone.border} flex items-center justify-center mb-4`}>
          <svg width="20" height="20" className={tone.text} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            {rolledBack ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            )}
          </svg>
        </div>

        <p className="text-lg font-bold text-slate-100 mb-2">{heading}</p>

        {/* The model was restored from backup -- say so plainly rather than
            leaving the counts to imply something landed. */}
        {rolledBack && (
          <div className="mb-5 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-left">
            <p className="text-sm text-red-300 font-medium mb-1">
              Your model was restored from backup. No changes were kept.
            </p>
            {result.error && <p className="text-xs text-red-400/80 break-words">{result.error}</p>}
          </div>
        )}

        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <p className="text-2xl font-black text-emerald-400 tabular-nums">{rolledBack ? 0 : result.applied}</p>
            <p className="text-xs text-emerald-500/70 font-medium mt-1">Written</p>
          </div>
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
            <p className="text-2xl font-black text-amber-400 tabular-nums">{result.deferred}</p>
            <p className="text-xs text-amber-500/70 font-medium mt-1">Deferred</p>
          </div>
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <p className="text-2xl font-black text-red-400 tabular-nums">{result.rejected}</p>
            <p className="text-xs text-red-500/70 font-medium mt-1">Rejected</p>
          </div>
        </div>

        {/* Findings that were accepted but have no mechanical fix. Listing them
            keeps "we chose not to" distinct from "it worked". */}
        {result.unsupported.length > 0 && (
          <details className="mb-4 text-left">
            <summary className="text-xs font-bold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-300">
              {result.unsupported.length} need a modelling decision
            </summary>
            <ul className="mt-2 space-y-2 max-h-40 overflow-y-auto">
              {result.unsupported.map((u) => (
                <li key={u.finding_id} className="text-xs bg-slate-800/50 rounded p-2 border border-slate-700/50">
                  <span className="text-slate-300 font-medium">{u.object}</span>
                  <span className="text-slate-500"> · {u.check}</span>
                  <p className="text-slate-400 mt-1">{u.reason}</p>
                </li>
              ))}
            </ul>
          </details>
        )}

        {result.failed.length > 0 && !rolledBack && (
          <details className="mb-4 text-left" open>
            <summary className="text-xs font-bold text-red-400 uppercase tracking-wider cursor-pointer">
              {result.failed.length} failed to write
            </summary>
            <ul className="mt-2 space-y-2 max-h-40 overflow-y-auto">
              {result.failed.map((f) => (
                <li key={f.finding_id} className="text-xs bg-red-500/5 rounded p-2 border border-red-500/20">
                  <span className="text-slate-300 font-medium">{f.object}</span>
                  <p className="text-red-400/80 mt-1">{f.detail}</p>
                </li>
              ))}
            </ul>
          </details>
        )}

        {result.new_score !== null && !rolledBack && (
          <div className="mb-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
            <p className="text-xs text-slate-500 uppercase tracking-wider font-bold mb-2">
              Score after re-scan
            </p>
            <div className="flex items-center justify-center gap-3">
              <span className="text-lg text-slate-500 tabular-nums">{preScore}</span>
              <svg width="16" height="16" className="text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
              <span className="text-lg font-bold text-blue-400 tabular-nums">{result.new_score}</span>
            </div>
          </div>
        )}

        {result.backup_path && (
          <p className="mb-4 text-[11px] text-slate-600 break-all" title={result.backup_path}>
            Backup: {result.backup_path.split(/[/\\]/).pop()}
          </p>
        )}

        <div className="flex gap-2 justify-center">
          <button className="btn-ghost text-sm px-4 py-2" onClick={onViewHistory}>View History</button>
          <button className="btn-primary text-sm px-4 py-2" onClick={onNewScan}>New Scan</button>
        </div>
      </div>
    </div>
  );
}
