// D:\FYP\FORGE-1\frontend\src\components\clarification\StartOverDialog.tsx
"use client";

// One project = one website (D-200). Starting over replaces the current website plan, so it is
// confirmed first; the old request stays in the project's history as cancelled.

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/services/client";

interface StartOverDialogProps {
  onKeep: () => void;
  onStartOver: () => Promise<void>;
}

export function StartOverDialog({ onKeep, onStartOver }: StartOverDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      await onStartOver();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start over. Please try again.");
      setBusy(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onKeep();
      }}
      aria-labelledby="start-over-title"
      className="m-auto w-[min(92vw,28rem)] rounded-2xl border border-line bg-surface p-0 text-ink shadow-card backdrop:bg-ink/40"
    >
      <div className="p-6">
        <h2 id="start-over-title" className="text-[18px] font-semibold">
          Start over?
        </h2>
        <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">
          This replaces your current website plan. Your earlier requests stay in this project’s history.
        </p>
        <p className="mt-3 text-[14px] leading-relaxed text-ink-muted">
          Building a different website?{" "}
          <Link href="/projects" className="font-medium text-ember-strong underline-offset-2 hover:underline">
            Create a new project
          </Link>{" "}
          instead.
        </p>
        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-alert-soft px-3.5 py-2.5 text-[14px] text-alert">
            {error}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onKeep}
            disabled={busy}
            className="rounded-lg px-4 py-2.5 text-[14px] font-medium text-ink-muted hover:bg-surface-sunk hover:text-ink disabled:opacity-40"
          >
            Keep my website
          </button>
          <button
            type="button"
            onClick={confirm}
            disabled={busy}
            className="rounded-lg bg-ink px-4 py-2.5 text-[14px] font-medium text-paper transition-colors hover:bg-ember-strong disabled:opacity-40"
          >
            {busy ? "Starting over…" : "Start over"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
