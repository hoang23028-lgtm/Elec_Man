"use client";

import { useEffect, useRef } from "react";

export function usePolling(
  callback: () => Promise<unknown>,
  intervalMs: number,
  enabled = true,
): void {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    let running = false;
    let disposed = false;

    async function run() {
      if (disposed || running || document.hidden) return;
      running = true;
      try {
        await callbackRef.current();
      } catch {
        // Polling callbacks surface their own UI errors; keep the timer alive.
      } finally {
        running = false;
      }
    }

    const handleVisibility = () => {
      if (!document.hidden) void run();
    };
    const timer = window.setInterval(() => void run(), intervalMs);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      disposed = true;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [enabled, intervalMs]);
}
