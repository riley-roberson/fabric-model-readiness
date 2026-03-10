import { useCallback, useRef } from "react";
import type { ScanResult, ApplyRequest, ApplyResult } from "@/types/scan";
import type { EnrichedModelHistory, DeferredItem } from "@/types/history";

function getBackendUrl(): string {
  const params = new URLSearchParams(window.location.search);
  const port = params.get("port") || "8000";
  return `http://127.0.0.1:${port}`;
}

export function useApi() {
  const baseUrl = useRef(getBackendUrl());

  const scan = useCallback(async (path: string): Promise<ScanResult> => {
    const res = await fetch(`${baseUrl.current}/api/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Scan failed");
    }
    return res.json();
  }, []);

  const scanStream = useCallback(
    (
      path: string,
      onProgress: (data: { step: string; percent: number; message: string }) => void,
      onResult: (data: ScanResult) => void,
      onError: (err: string) => void
    ) => {
      const controller = new AbortController();

      fetch(`${baseUrl.current}/api/scan/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
        signal: controller.signal,
      })
        .then(async (res) => {
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            onError(err.detail || "Scan failed");
            return;
          }
          const reader = res.body?.getReader();
          if (!reader) return;

          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const eventData = line.slice(6);
                // Look at the previous line for event type
                try {
                  const parsed = JSON.parse(eventData);
                  if (parsed.step) {
                    onProgress(parsed);
                  } else if (parsed.scan_id) {
                    onResult(parsed);
                  } else if (parsed.message && !parsed.step) {
                    onError(parsed.message);
                  }
                } catch {
                  // skip non-JSON lines
                }
              }
            }
          }
        })
        .catch((err) => {
          if (err.name !== "AbortError") {
            onError(err.message);
          }
        });

      return () => controller.abort();
    },
    []
  );

  const apply = useCallback(async (request: ApplyRequest): Promise<ApplyResult> => {
    const res = await fetch(`${baseUrl.current}/api/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Apply failed");
    }
    return res.json();
  }, []);

  const getHistory = useCallback(async (modelName?: string): Promise<EnrichedModelHistory | { models: string[] }> => {
    const url = modelName
      ? `${baseUrl.current}/api/history/${encodeURIComponent(modelName)}`
      : `${baseUrl.current}/api/history`;
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to load history");
    }
    return res.json();
  }, []);

  const getDeferredItems = useCallback(async (modelName: string): Promise<{ modelName: string; items: DeferredItem[] }> => {
    const res = await fetch(`${baseUrl.current}/api/history/${encodeURIComponent(modelName)}/deferred`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to load deferred items");
    }
    return res.json();
  }, []);

  const healthCheck = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${baseUrl.current}/api/health`);
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  return { scan, scanStream, apply, getHistory, getDeferredItems, healthCheck };
}
