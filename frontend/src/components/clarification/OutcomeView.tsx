// D:\FYP\FORGE-1\frontend\src\components\clarification\OutcomeView.tsx
"use client";

import { RequestEnvelope } from "@/types/request";

type Outcome = Extract<RequestEnvelope, { status: "complete" | "out_of_scope" | "failed" | "cancelled" }>;

type Stopped = Extract<RequestEnvelope, { status: "paused" | "processing" }>;

/** A run that stopped mid-way (paused) or is still running in another tab or request (processing). */
export function StoppedView({ run, onContinue, onCancel, onCheckAgain }: {
  run: Stopped;
  onContinue: () => void;
  onCancel: () => void;
  onCheckAgain: () => void;
}) {
  const paused = run.status === "paused";
  return (
    <section aria-labelledby="outcome-title" className="animate-rise">
      <Heading eyebrow={paused ? "Paused" : "Still working"} title={paused ? "Pick up where you left off." : "FORGE is still on it."} />
      <p className="mt-5 max-w-[60ch] text-[16px] leading-relaxed text-ink">{run.data.message}</p>
      <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
        <PrimaryButton onClick={paused ? onContinue : onCheckAgain}>{paused ? "Continue" : "Check again"}</PrimaryButton>
        {paused && (
          <button
            type="button"
            onClick={onCancel}
            className="text-[14px] font-medium text-ink-muted transition-colors duration-200 hover:text-ink"
          >
            Cancel this request
          </button>
        )}
      </div>
    </section>
  );
}

interface OutcomeViewProps {
  outcome: Outcome;
  onStartOver: () => void;
  onRetry?: () => void;
}

const TEST_KIND: Record<string, string> = {
  happy_path: "Works as expected",
  negative: "Handles a mistake",
  visual: "Looks right",
};

function PrimaryButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg bg-ink px-5 py-2.5 text-[14px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px"
    >
      {children}
    </button>
  );
}

function Heading({ eyebrow, title, tone = "ember" }: { eyebrow: string; title: string; tone?: "ember" | "positive" | "alert" }) {
  const colour = tone === "positive" ? "text-positive" : tone === "alert" ? "text-alert" : "text-ember-strong";
  return (
    <>
      <p className={`text-[13px] font-medium ${colour}`}>{eyebrow}</p>
      <h1
        id="outcome-title"
        className="mt-3 max-w-[20ch] font-display text-[2.3rem] leading-[1.05] tracking-[-0.01em] text-ink sm:text-[2.9rem]"
      >
        {title}
      </h1>
    </>
  );
}

export function OutcomeView({ outcome, onStartOver, onRetry }: OutcomeViewProps) {
  if (outcome.status === "complete") {
    const { requirement, test_cases } = outcome.data;
    const featureNames = new Map(requirement.features.map((f) => [f.id, f.name]));
    return (
      <section aria-labelledby="outcome-title" className="animate-rise">
        <Heading eyebrow="Step 4 · Brief ready" title="Your website brief is ready." tone="positive" />
        <p className="mt-5 max-w-[62ch] text-[16px] leading-relaxed text-ink">{requirement.clarified_text}</p>

        <dl className="mt-8 grid grid-cols-3 border-y border-line">
          {[
            ["Pages", requirement.pages.length],
            ["Features", requirement.features.length],
            ["Checks", test_cases.length],
          ].map(([label, value], i) => (
            <div key={label} className={`py-5 ${i > 0 ? "border-l border-line pl-5" : ""}`}>
              <dt className="text-[13px] text-ink-muted">{label}</dt>
              <dd className="mt-1 font-display text-[2.2rem] leading-none tabular-nums text-ink">{value}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-8 grid gap-8 sm:grid-cols-[1fr_1.4fr]">
          <div>
            <h2 className="text-[13px] font-medium text-ink-muted">Pages and sections</h2>
            <ul className="mt-3 space-y-3">
              {requirement.pages.map((page) => (
                <li key={page.name}>
                  <p className="text-[15px] font-medium capitalize text-ink">{page.name}</p>
                  {page.sections.length > 0 && (
                    <p className="text-[13px] text-ink-muted">
                      {page.sections.map((s) => featureNames.get(s) ?? s).join(", ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="text-[13px] font-medium text-ink-muted">
              How the finished site will be checked
            </h2>
            <p className="mt-1 text-[13px] text-ink-faint">
              Written from your brief before anything is built.
            </p>
            <ol className="mt-3 divide-y divide-line border-y border-line">
              {test_cases.map((t) => (
                <li key={t.test_id} className="flex gap-3 py-2.5">
                  <span className="pt-0.5 font-mono text-[12px] tabular-nums text-ink-faint">{t.test_id}</span>
                  <span className="flex flex-col">
                    <span className="text-[14px] text-ink">{t.description}</span>
                    <span className="text-[12px] text-ink-muted">
                      {TEST_KIND[t.kind]} · {featureNames.get(t.requirement_ref) ?? t.requirement_ref}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-line pt-6">
          <PrimaryButton onClick={onStartOver}>Start over</PrimaryButton>
          <p className="text-[13px] text-ink-muted">The build stage will work from this brief.</p>
        </div>
      </section>
    );
  }

  if (outcome.status === "out_of_scope") {
    return (
      <section aria-labelledby="outcome-title" className="animate-rise">
        <Heading eyebrow="Outside what FORGE builds" title="FORGE can't build this one." />
        <p className="mt-5 max-w-[60ch] text-[16px] leading-relaxed text-ink">{outcome.data.reason}</p>
        {outcome.data.alternatives.length > 0 && (
          <div className="mt-6 rounded-lg bg-surface-sunk px-4 py-3">
            <p className="text-[13px] font-medium text-ink-muted">What FORGE can do instead</p>
            <ul className="mt-1.5 space-y-1 text-[15px] text-ink">
              {outcome.data.alternatives.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="mt-8">
          <PrimaryButton onClick={onStartOver}>Describe a different website</PrimaryButton>
        </div>
      </section>
    );
  }

  if (outcome.status === "failed") {
    const { category, message, missing } = outcome.data;
    return (
      <section aria-labelledby="outcome-title" className="animate-rise">
        <Heading
          eyebrow={category === "system" ? "Technical problem" : "We need more detail"}
          title={category === "system" ? "Something went wrong on our side." : "We couldn't finish your summary."}
          tone="alert"
        />
        <p className="mt-5 max-w-[60ch] text-[16px] leading-relaxed text-ink">{message}</p>
        {missing.length > 0 && (
          <ul className="mt-4 list-disc space-y-1 pl-5 text-[15px] text-ink">
            {missing.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          {category === "system" && onRetry ? (
            <>
              <PrimaryButton onClick={onRetry}>Try again</PrimaryButton>
              <button
                type="button"
                onClick={onStartOver}
                className="text-[14px] font-medium text-ink-muted transition-colors duration-200 hover:text-ink"
              >
                Start over
              </button>
            </>
          ) : (
            <PrimaryButton onClick={onStartOver}>Start again</PrimaryButton>
          )}
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="outcome-title" className="animate-rise">
      <Heading eyebrow="Cancelled" title="Request cancelled." />
      <p className="mt-5 text-[16px] text-ink-muted">Nothing was built. You can start a new request at any time.</p>
      <div className="mt-8">
        <PrimaryButton onClick={onStartOver}>Describe a website</PrimaryButton>
      </div>
    </section>
  );
}
