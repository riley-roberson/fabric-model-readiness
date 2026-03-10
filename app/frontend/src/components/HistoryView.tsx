import { useState, useEffect } from "react";
import { useApi } from "@/hooks/useApi";
import type { EnrichedModelHistory } from "@/types/history";
import { HistorySessionCard } from "./HistorySessionCard";

interface HistoryViewProps {
  modelName?: string;
  onBack: () => void;
}

export function HistoryView({ modelName, onBack }: HistoryViewProps) {
  const { getHistory } = useApi();
  const [history, setHistory] = useState<EnrichedModelHistory | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>(modelName || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    if (selectedModel) {
      getHistory(selectedModel)
        .then((data) => {
          setHistory(data as EnrichedModelHistory);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    } else {
      getHistory()
        .then((data) => {
          setModels((data as { models: string[] }).models);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [selectedModel, getHistory]);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <button
          className="btn-ghost text-xs px-3 py-1.5 rounded-lg"
          onClick={() => {
            if (history && !modelName) {
              setHistory(null);
              setSelectedModel("");
            } else {
              onBack();
            }
          }}
        >
          <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Back
        </button>
        <h2 className="text-base font-bold text-slate-100">
          {history ? history.modelName : "History"}
        </h2>
      </div>

      {/* Loading / Error states */}
      {loading && (
        <div className="card p-6 text-center">
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      )}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Model selector */}
      {!selectedModel && models.length > 0 && !loading && (
        <div className="space-y-1.5">
          <p className="text-sm text-slate-500 mb-2">Select a model:</p>
          {models.map((m) => (
            <button
              key={m}
              className="card-hover w-full text-left px-4 py-3 flex items-center gap-3"
              onClick={() => setSelectedModel(m)}
            >
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                <svg width="16" height="16" className="text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
                </svg>
              </div>
              <span className="text-sm font-medium text-slate-200">{m}</span>
              <svg width="12" height="12" className="text-slate-600 ml-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          ))}
        </div>
      )}

      {!selectedModel && models.length === 0 && !loading && (
        <div className="card p-6 text-center">
          <p className="text-sm text-slate-500">No history found.</p>
        </div>
      )}

      {/* Session list (most recent first) */}
      {history && Array.isArray(history.sessions) && (
        <div className="space-y-6">
          {[...history.sessions].reverse().map((session, idx) => (
            <HistorySessionCard
              key={session?.sessionId ?? idx}
              session={session}
              deferredItems={history.deferredItems ?? []}
            />
          ))}
        </div>
      )}
      {history && !Array.isArray(history.sessions) && (
        <div className="card p-4">
          <p className="text-sm text-slate-500">History data has an unexpected format.</p>
          <pre className="text-xs text-slate-600 mt-2 overflow-auto max-h-40">
            {JSON.stringify(Object.keys(history), null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
