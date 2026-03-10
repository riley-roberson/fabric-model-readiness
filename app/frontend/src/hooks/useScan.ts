import { useState, useCallback } from "react";
import type { ScanResult, ScanProgress, AppScreen } from "@/types/scan";
import { useApi } from "./useApi";

export function useScan() {
  const { scanStream } = useApi();
  const [screen, setScreen] = useState<AppScreen>("drop");
  const [progress, setProgress] = useState<ScanProgress>({ step: "", percent: 0, message: "" });
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startScan = useCallback(
    (path: string) => {
      setScreen("scanning");
      setError(null);
      setProgress({ step: "starting", percent: 0, message: "Starting scan..." });

      const cancel = scanStream(
        path,
        (prog) => setProgress(prog),
        (data) => {
          setResult(data);
          setScreen("results");
        },
        (err) => {
          setError(err);
          setScreen("drop");
        }
      );

      return cancel;
    },
    [scanStream]
  );

  const reset = useCallback(() => {
    setScreen("drop");
    setProgress({ step: "", percent: 0, message: "" });
    setResult(null);
    setError(null);
  }, []);

  return {
    screen,
    setScreen,
    progress,
    result,
    error,
    startScan,
    reset,
  };
}
