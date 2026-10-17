// D:\FYP\FORGE-1\frontend\src\components\clarification\StudioHeader.tsx
"use client";

export type Step = "describe" | "answer" | "confirm" | "brief";

const STEPS: { id: Step; label: string }[] = [
  { id: "describe", label: "Describe" },
  { id: "answer", label: "Answer" },
  { id: "confirm", label: "Confirm" },
  { id: "brief", label: "Brief" },
];

function ForgeMark() {
  // Anvil-like mark: a striking face over a tapered base.
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className="h-7 w-7">
      <rect x="3" y="7" width="26" height="6" rx="1.5" className="fill-ink" />
      <path d="M10 13h12l-2.5 7h-7z" className="fill-ink" />
      <rect x="8" y="21" width="16" height="4" rx="1" className="fill-ember" />
    </svg>
  );
}

interface StudioHeaderProps {
  step: Step;
  onStartOver?: () => void;
  busy?: boolean;
}

export function StudioHeader({ step, onStartOver, busy }: StudioHeaderProps) {
  const current = STEPS.findIndex((s) => s.id === step);

  return (
    <header className="relative z-10 border-b border-line/70">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-6 px-5 py-4 sm:px-8">
        <div className="flex items-center gap-2.5">
          <ForgeMark />
          <span className="text-[15px] font-semibold tracking-[0.18em] text-ink">FORGE</span>
        </div>

        <nav aria-label="Progress" className="hidden sm:block">
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

        {onStartOver ? (
          <button
            type="button"
            onClick={onStartOver}
            disabled={busy}
            className="rounded-md px-3 py-2 text-[13px] font-medium text-ink-muted transition-colors duration-200 hover:bg-surface-sunk hover:text-ink disabled:opacity-40"
          >
            New website
          </button>
        ) : (
          <span className="w-[92px]" aria-hidden="true" />
        )}
      </div>
    </header>
  );
}
