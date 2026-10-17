// D:\FYP\FORGE-1\frontend\src\components\projects\DeleteProjectDialog.tsx
"use client";

// Deleting is for good (D-174, D-180): the project, its requests and their saved progress.
// The user types the project's name to confirm, so it can't happen by a slip of the finger.

import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError } from "@/services/client";
import { Project } from "@/types/auth";

interface DeleteProjectDialogProps {
  project: Project;
  onCancel: () => void;
  onDelete: (project: Project) => Promise<void>;
}

export function DeleteProjectDialog({ project, onCancel, onDelete }: DeleteProjectDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const matches = typed.trim().toLowerCase() === project.name.trim().toLowerCase();

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!matches || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onDelete(project);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The project could not be deleted. Please try again.");
      setBusy(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onCancel();
      }}
      aria-labelledby="delete-title"
      className="m-auto w-[min(92vw,28rem)] rounded-2xl border border-line bg-surface p-0 text-ink shadow-card backdrop:bg-ink/40"
    >
      <form onSubmit={submit} className="p-6">
        <h2 id="delete-title" className="text-[18px] font-semibold">
          Delete “{project.name}”?
        </h2>
        <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">
          This deletes the project, every website request in it and their saved progress. It can’t be undone.
        </p>
        <label className="mt-5 block text-[14px] font-medium">
          Type <span className="font-semibold">{project.name}</span> to confirm
          <input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            autoFocus
            autoComplete="off"
            spellCheck={false}
            className="mt-1.5 block w-full rounded-lg border border-line bg-paper px-3.5 py-2.5 text-[15px] focus:border-alert focus:outline-none focus:ring-2 focus:ring-alert/25"
          />
        </label>
        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-alert-soft px-3.5 py-2.5 text-[14px] text-alert">
            {error}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-lg px-4 py-2.5 text-[14px] font-medium text-ink-muted hover:bg-surface-sunk hover:text-ink disabled:opacity-40"
          >
            Keep it
          </button>
          <button
            type="submit"
            disabled={!matches || busy}
            className="rounded-lg bg-alert px-4 py-2.5 text-[14px] font-medium text-paper transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {busy ? "Deleting…" : "Delete for good"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
