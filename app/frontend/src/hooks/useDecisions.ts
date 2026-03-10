import { useState, useCallback, useMemo } from "react";
import type { Disposition } from "@/types/findings";

export interface Decision {
  findingId: string;
  action: Disposition;
  reason?: string;
}

export function useDecisions() {
  const [decisions, setDecisions] = useState<Map<string, Decision>>(new Map());

  const setDecision = useCallback((findingId: string, action: Disposition, reason?: string) => {
    setDecisions((prev) => {
      const next = new Map(prev);
      next.set(findingId, { findingId, action, reason });
      return next;
    });
  }, []);

  const clearDecision = useCallback((findingId: string) => {
    setDecisions((prev) => {
      const next = new Map(prev);
      next.delete(findingId);
      return next;
    });
  }, []);

  const acceptAll = useCallback((findingIds: string[]) => {
    setDecisions((prev) => {
      const next = new Map(prev);
      for (const id of findingIds) {
        next.set(id, { findingId: id, action: "accepted" });
      }
      return next;
    });
  }, []);

  const resetAll = useCallback(() => {
    setDecisions(new Map());
  }, []);

  const counts = useMemo(() => {
    let accepted = 0;
    let rejected = 0;
    let deferred = 0;
    for (const d of decisions.values()) {
      if (d.action === "accepted") accepted++;
      else if (d.action === "rejected") rejected++;
      else if (d.action === "deferred") deferred++;
    }
    return { accepted, rejected, deferred, total: decisions.size };
  }, [decisions]);

  return {
    decisions,
    setDecision,
    clearDecision,
    acceptAll,
    resetAll,
    counts,
  };
}
