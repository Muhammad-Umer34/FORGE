// D:\FYP\FORGE-1\frontend\src\components\clarification\StudioHeader.tsx
"use client";

// The header of every signed-in page: FORGE mark, where you are (Projects / project name),
// the four steps while a request is open, and the account menu.

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";

export type Step = "describe" | "answer" | "confirm" | "brief";

const STEPS: { id: Step; label: string }[] = [
  { id: "describe", label: "Describe" },
  { id: "answer", label: "Answer" },
  { id: "confirm", label: "Confirm" },
  { id: "brief", label: "Brief" },
];

export function ForgeMark() {
  // Anvil-like mark: a striking face over a tapered base.
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className="h-7 w-7 shrink-0">
      <rect x="3" y="7" width="26" height="6" rx="1.5" className="fill-ink" />
      <path d="M10 13h12l-2.5 7h-7z" className="fill-ink" />
      <rect x="8" y="21" width="16" height="4" rx="1" className="fill-ember" />
    </svg>
  );
}

function AccountMenu() {
  const { user, logout } = useAuth();
  const [leaving, setLeaving] = useState(false);
  if (!user) return null;

  const signOut = async () => {
    setLeaving(true);
    await logout(); // the page guard then opens the sign-in page
  };

  return (
    <div className="flex items-center gap-2">
      <span
        title={user.email}
        aria-hidden="true"
        className="hidden h-8 w-8 items-center justify-center rounded-full bg-ember-soft text-[13px] font-semibold text-ember-strong sm:flex"
      >
        {user.display_name.trim().charAt(0).toUpperCase() || "?"}
      </span>
      <button
        type="button"
        onClick={signOut}
        disabled={leaving}
        className="rounded-md px-3 py-2 text-[13px] font-medium text-ink-muted transition-colors duration-200 hover:bg-surface-sunk hover:text-ink disabled:opacity-40"
      >
        {leaving ? "Signing out…" : "Sign out"}
      </button>
    </div>
  );
}

interface StudioHeaderProps {
  step?: Step;                 // shows the progress steps (project page only)
  projectName?: string;        // shows "Projects / name" as a way back
  onStartOver?: () => void;
  busy?: boolean;
}

export function StudioHeader({ step, projectName, onStartOver, busy }: StudioHeaderProps) {
  const current = step ? STEPS.findIndex((s) => s.id === step) : -1;

  return (
    <header className="relative z-10 border-b border-line/70">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
        <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2.5">
          <Link href="/projects" className="flex shrink-0 items-center gap-2.5 rounded-md" aria-label="FORGE, your projects">
            <ForgeMark />
            <span className="text-[15px] font-semibold tracking-[0.18em] text-ink">FORGE</span>
          </Link>
          {projectName && (
            <>
              <span aria-hidden="true" className="text-ink-faint">/</span>
              <Link href="/projects" className="hidden text-[14px] text-ink-muted hover:text-ink sm:inline">
                Projects
              </Link>
              <span aria-hidden="true" className="hidden text-ink-faint sm:inline">/</span>
              <span aria-current="page" className="truncate text-[14px] font-medium text-ink">
                {projectName}
              </span>
            </>
          )}
        </nav>

        {step && (
          <nav aria-label="Progress" className="hidden lg:block">
            <ol className="flex items-center gap-1 text-[13px]">
              {STEPS.map((s, i) => {
                const state = i < current ? "done" : i === current ? "current" : "next";
                return (
                  <li key={s.id} className="flex items-center gap-1">
                    <span
                      aria-current={state === "current" ? "step" : undefined}
                      className={
                        state === "current"
                          ? "rounded-md bg-ember-soft px-2.5 py-1 font-medium text-ember-strong"
                          : state === "done"
                            ? "px-2.5 py-1 text-ink-muted"
                            : "px-2.5 py-1 text-ink-faint"
                      }
                    >
                      {s.label}
                    </span>
                    {i < STEPS.length - 1 && <span aria-hidden="true" className="h-px w-4 bg-line" />}
                  </li>
                );
              })}
            </ol>
          </nav>
        )}

        <div className="flex shrink-0 items-center gap-1">
          {onStartOver && (
            <button
              type="button"
              onClick={onStartOver}
              disabled={busy}
              className="rounded-md px-3 py-2 text-[13px] font-medium text-ink-muted transition-colors duration-200 hover:bg-surface-sunk hover:text-ink disabled:opacity-40"
            >
              Start over
            </button>
          )}
          <AccountMenu />
        </div>
      </div>
    </header>
  );
}
