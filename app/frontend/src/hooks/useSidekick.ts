import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ProcessDefinition,
  ProjectState,
  StageFindings,
  StepStatus,
} from "@/types/sidekick";

function getBackendUrl(): string {
  const params = new URLSearchParams(window.location.search);
  const port = params.get("port") || "8000";
  return `http://127.0.0.1:${port}`;
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export function useSidekick() {
  const baseUrl = useRef(getBackendUrl());
  const [process, setProcess] = useState<ProcessDefinition | null>(null);
  const [state, setState] = useState<ProjectState | null>(null);
  const [findings, setFindings] = useState<StageFindings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // The process definition is static; fetch it once.
  useEffect(() => {
    fetch(`${baseUrl.current}/api/sidekick/process`)
      .then((res) => unwrap<ProcessDefinition>(res))
      .then(setProcess)
      .catch((e) => setError(e.message));
  }, []);

  const openProject = useCallback(
    async (rootPath: string, opts?: { name?: string; size?: string; modelPath?: string }) => {
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(`${baseUrl.current}/api/sidekick/project`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            root_path: rootPath,
            name: opts?.name ?? "",
            size: opts?.size ?? "medium",
            model_path: opts?.modelPath ?? "",
          }),
        });
        const data = await unwrap<{ created: boolean; state: ProjectState }>(res);
        setState(data.state);
        return data;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not open the project");
        return null;
      } finally {
        setBusy(false);
      }
    },
    []
  );

  const markStep = useCallback(
    async (stepId: string, status: StepStatus, opts?: { note?: string; reason?: string }) => {
      if (!state) return;
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(`${baseUrl.current}/api/sidekick/step`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            root_path: state.root_path,
            step_id: stepId,
            state: status,
            note: opts?.note ?? "",
            reason: opts?.reason ?? "",
          }),
        });
        setState(await unwrap<ProjectState>(res));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not update the step");
      } finally {
        setBusy(false);
      }
    },
    [state]
  );

  const attestGate = useCallback(
    async (gateId: string, attestedBy: string, note = "") => {
      if (!state) return;
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(`${baseUrl.current}/api/sidekick/gate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            root_path: state.root_path,
            gate_id: gateId,
            attested_by: attestedBy,
            note,
          }),
        });
        setState(await unwrap<ProjectState>(res));
      } catch (e) {
        // A 409 here is the gate doing its job, not a fault.
        setError(e instanceof Error ? e.message : "Could not record the attestation");
      } finally {
        setBusy(false);
      }
    },
    [state]
  );

  const setStage = useCallback(
    async (stageId: string) => {
      if (!state) return;
      setBusy(true);
      try {
        const res = await fetch(`${baseUrl.current}/api/sidekick/stage`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ root_path: state.root_path, stage_id: stageId }),
        });
        setState(await unwrap<ProjectState>(res));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not change stage");
      } finally {
        setBusy(false);
      }
    },
    [state]
  );

  const refreshFindings = useCallback(async () => {
    if (!state) return;
    try {
      const url = `${baseUrl.current}/api/sidekick/findings?root_path=${encodeURIComponent(state.root_path)}`;
      setFindings(await unwrap<StageFindings>(await fetch(url)));
    } catch {
      setFindings(null); // a model that will not parse is not a Sidekick failure
    }
  }, [state]);

  // Findings are stage-scoped, so they change whenever the stage does.
  useEffect(() => {
    if (state?.model_path) void refreshFindings();
  }, [state?.current_stage, state?.model_path, refreshFindings]);

  return {
    process,
    state,
    findings,
    error,
    busy,
    openProject,
    markStep,
    attestGate,
    setStage,
    refreshFindings,
    clearError: () => setError(null),
  };
}
