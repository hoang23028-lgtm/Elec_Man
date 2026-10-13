"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ConfirmationGate } from "@/lib/confirmation-gate";

export type ConfirmationOptions = {
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
};

export function useConfirmationDialog() {
  const gate = useRef(new ConfirmationGate());
  const alive = useRef(true);
  const trigger = useRef<HTMLElement | null>(null);
  const [request, setRequest] = useState<ConfirmationOptions | null>(null);

  useEffect(() => {
    const current = gate.current;
    alive.current = true;
    return () => { alive.current = false; current.finish(false); };
  }, []);

  const ask = useCallback((options: ConfirmationOptions): Promise<boolean> => {
    if (!alive.current) return Promise.resolve(false);
    const decision = gate.current.begin();
    if (!decision) return Promise.resolve(false);
    trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setRequest(options);
    return decision;
  }, []);

  const finish = useCallback((accepted: boolean) => {
    gate.current.finish(accepted);
    if (alive.current) setRequest(null);
    const returnTarget = trigger.current;
    window.requestAnimationFrame(() => {
      if (alive.current && returnTarget?.isConnected && !returnTarget.matches(":disabled")) returnTarget.focus();
    });
  }, []);

  return { request, ask, finish };
}
