import { useState, useCallback } from "react";
import { DropZone } from "@/components/DropZone";
import { ScanProgress } from "@/components/ScanProgress";
import { ScoreCard } from "@/components/ScoreCard";
import { FindingsPanel } from "@/components/FindingsPanel";
import { ApplyButton } from "@/components/ApplyButton";
import { ResultsSummary } from "@/components/ResultsSummary";
import { HistoryView } from "@/components/HistoryView";
import { NavBar } from "@/components/NavBar";
import { StandardsDrawer } from "@/components/StandardsDrawer";
import { useScan } from "@/hooks/useScan";
import { useDecisions } from "@/hooks/useDecisions";
import { useApi } from "@/hooks/useApi";
import type { ApplyResult } from "@/types/scan";

export default function App() {
  const { screen, setScreen, progress, result, error, startScan, reset } = useScan();
  const { decisions, setDecision, acceptAll, resetAll, counts } = useDecisions();
  const { apply } = useApi();
  const [modelPath, setModelPath] = useState("");
  const [isApplying, setIsApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applyResult, setApplyResult] = useState<ApplyResult | null>(null);
  const [standardsOpen, setStandardsOpen] = useState(false);

  const handleSelect = useCallback(
    (path: string) => {
      setModelPath(path);
      resetAll();
      setApplyResult(null);
      startScan(path);
    },
    [startScan, resetAll]
  );

  const handleApply = useCallback(async () => {
    if (!result) return;
    setIsApplying(true);
    setApplyError(null);

    try {
      const decisionList = Array.from(decisions.values()).map((d) => ({
        finding_id: d.findingId,
        action: d.action,
        reason: d.reason,
      }));

      const modelName = result.model_name || modelPath.split(/[/\\]/).pop() || modelPath;

      const res = await apply({
        scan_id: result.scan_id,
        model_name: modelName,
        decisions: decisionList,
      });

      setApplyResult(res);
      setScreen("applied");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Apply failed";
      console.error("Apply failed:", err);
      setApplyError(msg);
    } finally {
      setIsApplying(false);
    }
  }, [result, decisions, modelPath, apply, setScreen]);

  const handleNewScan = useCallback(() => {
    reset();
    resetAll();
    setApplyResult(null);
    setModelPath("");
  }, [reset, resetAll]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-950">
      {/* Header */}
      <header className="flex items-center gap-3 px-6 py-4 border-b border-slate-800/50 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
          <svg width="18" height="18" className="text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
          </svg>
        </div>
        <div>
          <h1 className="text-lg font-bold text-white leading-tight">Fabric Model AI Readiness</h1>
          <p className="text-xs text-slate-500">Semantic model analyzer for Copilot preparation</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-slate-700">v0.1.0</span>
          <button
            onClick={() => setStandardsOpen(true)}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            aria-label="Scoring standards"
            title="Scoring standards"
          >
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </header>

      <StandardsDrawer open={standardsOpen} onClose={() => setStandardsOpen(false)} />

      {/* Main content */}
      <main className="flex-1 overflow-y-auto px-6 py-4">
        {screen === "drop" && (
          <DropZone onSelect={handleSelect} error={error} />
        )}

        {screen === "scanning" && (
          <ScanProgress modelPath={modelPath} progress={progress} />
        )}

        {screen === "results" && result && (
          <div className="max-w-2xl mx-auto">
            <ScoreCard
              score={result.score}
              rating={result.rating}
              summary={result.summary}
            />
            <FindingsPanel
              findings={result.findings}
              decisions={decisions}
              onDecision={setDecision}
              onAcceptAll={acceptAll}
            />
            <ApplyButton
              acceptedCount={counts.accepted}
              isApplying={isApplying}
              onApply={handleApply}
            />
            {applyError && (
              <div className="mt-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                Apply failed: {applyError}
              </div>
            )}
          </div>
        )}

        {screen === "applied" && applyResult && (
          <ResultsSummary
            result={applyResult}
            preScore={result?.score ?? 0}
            onViewHistory={() => setScreen("history")}
            onNewScan={handleNewScan}
          />
        )}

        {screen === "history" && (
          <HistoryView
            modelName={result?.model_name || (modelPath ? modelPath.split(/[/\\]/).pop() : undefined)}
            onBack={() => setScreen(result ? "results" : "drop")}
          />
        )}
      </main>

      {/* Bottom navigation cards */}
      <NavBar
        currentScreen={screen}
        hasResults={result !== null}
        onNavigate={setScreen}
      />
    </div>
  );
}
