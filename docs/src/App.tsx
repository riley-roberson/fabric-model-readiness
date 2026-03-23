import { useCallback, useState } from "react";
import { FolderPicker } from "./components/FolderPicker";
import { ScanProgress } from "./components/ScanProgress";
import { ScoreCard } from "./components/ScoreCard";
import { FindingsPanel } from "./components/FindingsPanel";
import { ViewToggle } from "./components/ViewToggle";
import type { ViewMode } from "./components/ViewToggle";
import { ChecklistPanel } from "./components/ChecklistPanel";
import { useChecklist } from "./hooks/useChecklist";
import { parse } from "./scanner/parser";
import { runAllChecks } from "./scanner/rules";
import { computeSummary, estimateTotalChecks, rating } from "./scanner/scorer";
import type { ScanResult } from "./scanner/types";

type AppState = "idle" | "scanning" | "results" | "error";

export function App() {
  const [state, setState] = useState<AppState>("idle");
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [progress, setProgress] = useState({ step: "", percent: 0 });
  const [errorMsg, setErrorMsg] = useState("");
  const [modelName, setModelName] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("findings");

  const handleFolderSelect = useCallback(async (dir: FileSystemDirectoryHandle) => {
    setState("scanning");
    setErrorMsg("");

    const name = dir.name.endsWith(".SemanticModel")
      ? dir.name.slice(0, -".SemanticModel".length)
      : dir.name;
    setModelName(name);

    try {
      // Step 1: Parse
      setProgress({ step: "Parsing model files...", percent: 10 });
      const model = await parse(dir);

      // Step 2: Run rules
      setProgress({ step: "Running checks...", percent: 30 });
      const findings = runAllChecks(model, ({ current, total, module }) => {
        const pct = 30 + Math.round((current / total) * 60);
        setProgress({ step: `Checking: ${module}`, percent: pct });
      });

      // Step 3: Score
      setProgress({ step: "Computing score...", percent: 95 });
      const totalChecks = estimateTotalChecks(findings);
      const summary = computeSummary(findings, totalChecks);
      const score = summary.score;

      const result: ScanResult = {
        scan_id: crypto.randomUUID?.() ?? Date.now().toString(36),
        model_name: model.name,
        model_format: model.format,
        score,
        rating: rating(score),
        summary,
        findings,
      };

      setScanResult(result);
      setState("results");
    } catch (err) {
      console.error("Scan failed:", err);
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setState("error");
    }
  }, []);

  const checklist = useChecklist(
    scanResult?.findings ?? [],
    scanResult?.model_name ?? "",
  );

  const handleReset = useCallback(() => {
    setState("idle");
    setScanResult(null);
    setProgress({ step: "", percent: 0 });
    setErrorMsg("");
    setModelName("");
    setViewMode("findings");
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg width="20" height="20" className="text-brand-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082" />
            </svg>
            <span className="text-sm font-bold text-gray-900">Fabric Model Scout</span>
          </div>
          {state !== "idle" && (
            <button className="btn-ghost text-xs px-3 py-1.5" onClick={handleReset}>
              Scan Another
            </button>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-4 py-6">
        {state === "idle" && (
          <FolderPicker onSelect={handleFolderSelect} />
        )}

        {state === "scanning" && (
          <ScanProgress
            modelName={modelName}
            step={progress.step}
            percent={progress.percent}
          />
        )}

        {state === "results" && scanResult && (
          <div>
            <div className="mb-4">
              <h2 className="text-lg font-bold text-gray-900">
                {scanResult.model_name}
              </h2>
              <p className="text-xs text-gray-500">
                Format: {scanResult.model_format} &middot; {scanResult.findings.length} findings
              </p>
            </div>

            <ScoreCard
              score={scanResult.score}
              rating={scanResult.rating}
              summary={scanResult.summary}
            />

            <ViewToggle mode={viewMode} onModeChange={setViewMode} stats={checklist.stats} />

            {viewMode === "findings" ? (
              <FindingsPanel findings={scanResult.findings} />
            ) : (
              <ChecklistPanel findings={scanResult.findings} checklist={checklist} />
            )}
          </div>
        )}

        {state === "error" && (
          <div className="flex flex-col items-center justify-center min-h-[60vh]">
            <div className="card p-8 max-w-md w-full text-center">
              <div className="mx-auto w-14 h-14 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center mb-5">
                <svg width="28" height="28" className="text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              </div>
              <h2 className="text-lg font-bold text-gray-900 mb-2">Analysis Failed</h2>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed">{errorMsg}</p>
              <button className="btn-primary text-sm px-6 py-3" onClick={handleReset}>
                Try Again
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
