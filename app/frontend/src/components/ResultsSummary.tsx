import type { ApplyResult } from "@/types/scan";

interface ResultsSummaryProps {
  result: ApplyResult;
  preScore: number;
  onViewHistory: () => void;
  onNewScan: () => void;
}

export function ResultsSummary({ result, preScore, onViewHistory, onNewScan }: ResultsSummaryProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full">
      <div className="w-full max-w-sm card p-8 text-center">
        <div className="mx-auto w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
          <svg width="20" height="20" className="text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>

        <p className="text-lg font-bold text-slate-100 mb-6">Changes Applied</p>

        <div className="grid grid-cols-3 gap-2 mb-6">
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <p className="text-2xl font-black text-emerald-400 tabular-nums">{result.applied}</p>
            <p className="text-xs text-emerald-500/70 font-medium mt-1">Accepted</p>
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

        {result.new_score !== null && (
          <div className="mb-6 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
            <p className="text-xs text-slate-500 uppercase tracking-wider font-bold mb-2">Score</p>
            <div className="flex items-center justify-center gap-3">
              <span className="text-lg text-slate-500 tabular-nums">{preScore}</span>
              <svg width="16" height="16" className="text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
              <span className="text-lg font-bold text-blue-400 tabular-nums">{result.new_score}</span>
            </div>
          </div>
        )}

        <div className="flex gap-2 justify-center">
          <button className="btn-ghost text-sm px-4 py-2" onClick={onViewHistory}>View History</button>
          <button className="btn-primary text-sm px-4 py-2" onClick={onNewScan}>New Scan</button>
        </div>
      </div>
    </div>
  );
}
