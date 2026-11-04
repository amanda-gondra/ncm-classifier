"use client";

// Tracks whether the API can classify right now. The free Render instance sleeps after
// 15 minutes without traffic, so the first visit may find it asleep: the hook keeps
// asking /health until the model is ready, for up to `giveUpMs`.
import { useCallback, useEffect, useState } from "react";

import { getHealth } from "@/lib/api/client";

export type ApiStatus = "checking" | "waking" | "ready" | "unavailable";

export function useApiStatus(pollMs = 5_000, giveUpMs = 180_000) {
  const [status, setStatus] = useState<ApiStatus>("checking");
  const [round, setRound] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const startedAt = Date.now();
    let timer: ReturnType<typeof setTimeout> | undefined;

    const check = async () => {
      let next: ApiStatus = "waking";
      try {
        const health = await getHealth(controller.signal);
        if (health.status === "ok") next = "ready";
        else if (health.status === "unavailable") next = "unavailable";
      } catch {
        // Network failure or timeout: the server is probably still waking up.
      }
      if (controller.signal.aborted) return;
      if (next === "waking" && Date.now() - startedAt >= giveUpMs) next = "unavailable";
      setStatus(next);
      if (next === "waking") timer = setTimeout(check, pollMs);
    };

    void check();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [pollMs, giveUpMs, round]);

  const retry = useCallback(() => {
    setStatus("checking");
    setRound((value) => value + 1);
  }, []);

  return { status, retry };
}
