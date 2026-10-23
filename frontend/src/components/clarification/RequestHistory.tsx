// D:\FYP\FORGE-1\frontend\src\components\clarification\RequestHistory.tsx
"use client";

// Earlier website requests in this project (D-179), newest first. Opening one resumes it where it
// stopped, because every run is saved on the server.

import { RequestSummary } from "@/types/auth";

const STATUS_LABEL: Record<RequestSummary["status"], { text: string; tone: string }> = {
  processing: { text: "Working on it", tone: "bg-surface-sunk text-ink-muted" },
  paused: { text: "Paused – continue", tone: "bg-ember-soft text-ember-strong" },
  needs_clarification: { text: "Waiting for your answer", tone: "bg-ember-soft text-ember-strong" },
  awaiting_confirmation: { text: "Ready to confirm", tone: "bg-ember-soft text-ember-strong" },
  complete: { text: "Brief ready", tone: "bg-positive-soft text-positive" },
  out_of_scope: { text: "Not supported", tone: "bg-surface-sunk text-ink-muted" },
  failed: { text: "Needs more detail", tone: "bg-alert-soft text-alert" },
  cancelled: { text: "Cancelled", tone: "bg-surface-sunk text-ink-muted" },
};

const when = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });

interface RequestHistoryProps {
  requests: RequestSummary[];
  onOpen: (requestId: string) => void;
  busy: boolean;
}

export function RequestHistory({ requests, onOpen, busy }: RequestHistoryProps) {
  if (requests.length === 0) return null;
  return (
    <section aria-labelledby="history-title" className="mt-14">
      <h2 id="history-title" className="text-[13px] font-medium uppercase tracking-[0.14em] text-ink-faint">
        Earlier requests in this project
      </h2>
      <ul className="mt-3 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
        {requests.map((request) => {
          const label = STATUS_LABEL[request.status];
          return (
            <li key={request.id}>
              <button
                type="button"
                onClick={() => onOpen(request.id)}
                disabled={busy}
                className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-surface-sunk disabled:opacity-50"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[15px] text-ink">{request.prompt}</span>
                  <span className="mt-0.5 block text-[12px] text-ink-faint">{when.format(new Date(request.updated_at))}</span>
                </span>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-[12px] font-medium ${label.tone}`}>{label.text}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
