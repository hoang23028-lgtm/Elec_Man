"use client";

import { useEffect } from "react";

type LeaveState = { busy: string[]; drafts: string[] };

/** Collect guards once, including drafts in visited, hidden tabs. */
export function canLeavePage(): boolean {
  const state: LeaveState = { busy: [], drafts: [] };
  window.dispatchEvent(new CustomEvent("app-before-leave", { detail: state }));
  if (state.busy.length) {
    window.alert(`Đang ${state.busy.join(", ")}. Vui lòng chờ hoàn tất trước khi rời trang.`);
    return false;
  }
  return !state.drafts.length || window.confirm(`Có thay đổi chưa lưu: ${state.drafts.join(", ")}. Rời trang sẽ mất các thay đổi này. Tiếp tục?`);
}

export function useLeaveGuard(dirty: boolean, busy: boolean, label: string) {
  useEffect(() => {
    function unload(event: BeforeUnloadEvent) {
      if (!dirty && !busy) return;
      event.preventDefault(); event.returnValue = "";
    }
    function collect(event: Event) {
      const state = (event as CustomEvent<LeaveState>).detail;
      if (busy) state.busy.push(label);
      else if (dirty) state.drafts.push(label);
    }
    window.addEventListener("beforeunload", unload);
    window.addEventListener("app-before-leave", collect);
    return () => {
      window.removeEventListener("beforeunload", unload);
      window.removeEventListener("app-before-leave", collect);
    };
  }, [dirty, busy, label]);
}
