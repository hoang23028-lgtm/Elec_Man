"use client";

import { useEffect, useId, useRef } from "react";
import type { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";

export function ConfirmationDialog({ confirmation }: {
  confirmation: ReturnType<typeof useConfirmationDialog>;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  const { request, finish } = confirmation;

  useEffect(() => {
    if (!request) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    // showModal makes the background inert and keeps keyboard focus inside.
    dialog.showModal();
    cancelRef.current?.focus();
    return () => { if (dialog.open) dialog.close(); };
  }, [request]);

  if (!request) return null;
  return <dialog ref={dialogRef} className="confirmation-dialog" role="alertdialog"
    aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId}
    onKeyDown={(event) => {
      if (event.key !== "Tab") return;
      const controls = event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not([disabled])");
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first?.focus();
      }
    }}
    onCancel={(event) => { event.preventDefault(); finish(false); }}>
    <p className="eyebrow">Xác nhận thao tác</p>
    <h2 id={titleId}>{request.title}</h2>
    <p id={descriptionId}>{request.description}</p>
    <div className="confirmation-actions">
      <button ref={cancelRef} type="button" className="secondary" onClick={() => finish(false)}>Hủy</button>
      <button type="button" className={request.danger ? "danger" : undefined} onClick={() => finish(true)}>{request.confirmLabel}</button>
    </div>
  </dialog>;
}
