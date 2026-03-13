interface ScanProgressProps {
  modelName: string;
  step: string;
  percent: number;
}

export function ScanProgress({ modelName, step, percent }: ScanProgressProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="w-full max-w-sm card p-8 text-center">
        <div className="mx-auto w-10 h-10 rounded-lg bg-blue-600/10 border border-blue-500/20 flex items-center justify-center mb-4">
          <svg width="20" height="20" className="text-blue-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082" />
          </svg>
        </div>

        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Analyzing</p>
        <p className="text-base font-bold text-slate-200 mb-6 truncate">{modelName}</p>

        <div className="w-full bg-slate-800 rounded-full h-2 mb-3 overflow-hidden">
          <div
            className="bg-gradient-to-r from-blue-600 to-blue-400 h-2 rounded-full transition-all duration-300"
            style={{ width: `${percent}%` }}
          />
        </div>

        <p className="text-sm text-slate-400">{step}</p>
      </div>
    </div>
  );
}
