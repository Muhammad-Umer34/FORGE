// D:\FYP\FORGE-1\frontend\src\components\clarification\PlanReview.tsx
"use client";

// The plan summary (plan v2 step 8, D-204): the pages and their sections, the hero headline, the custom parts,
// what the site stores, and what the owner will be asked for. The user approves it, asks for one change, or
// cancels. Once approved, the same view is shown read-only.

import { useState } from "react";
import { PlanData, PlanDecision } from "@/types/request";

interface PlanReviewProps {
  plan: PlanData;
  approved: boolean;
  busy: boolean;
  error: string | null;
  onDecide: (decision: PlanDecision) => void;
  onStartOver: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line py-6">
      <h2 className="text-[13px] font-medium text-ink-muted">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

const linkButton = "text-[14px] font-medium text-ink-muted transition-colors duration-200 hover:text-ink";

export function PlanReview({ plan, approved, busy, error, onDecide, onStartOver }: PlanReviewProps) {
  const [editing, setEditing] = useState(false);
  const [changeText, setChangeText] = useState("");
  const [cancelArmed, setCancelArmed] = useState(false);

  return (
    <section aria-labelledby="plan-title" className="animate-rise">
      <p className={`text-[13px] font-medium ${approved ? "text-positive" : "text-ember-strong"}`}>
        {approved ? "Step 5 · Plan approved" : "Step 4 · Plan"}
      </p>
      <h1
        id="plan-title"
        className="mt-3 font-display text-[2.3rem] leading-[1.05] tracking-[-0.01em] text-ink sm:text-[2.9rem]"
      >
        {approved ? "Your site plan is approved." : "Here's the plan for your site."}
      </h1>
      <p className="mt-5 max-w-[62ch] text-[16px] leading-relaxed text-ink">
        Your site will have {plan.pages.length} {plan.pages.length === 1 ? "page" : "pages"}.
        {plan.stored.length > 0 && " What visitors send will appear in your project dashboard."}
      </p>

      {plan.notice && (
        <p role="status" className="mt-6 rounded-lg border-l-2 border-ember bg-ember-soft/60 px-4 py-3 text-[14px] text-ink">
          {plan.notice}
        </p>
      )}

      {plan.hero_headline && (
        <div className="mt-8 rounded-2xl border border-line bg-surface px-6 py-5">
          <p className="text-[13px] font-medium text-ink-muted">Your welcome headline</p>
          <p className="mt-2 font-display text-[1.7rem] leading-tight text-ink">{plan.hero_headline}</p>
          {plan.hero_alternatives.length > 0 && (
            <p className="mt-2 text-[13px] text-ink-faint">Also considered: {plan.hero_alternatives.join(" · ")}</p>
          )}
        </div>
      )}

      <div className="mt-8">
        <Section title="Pages and sections">
          <ul className="space-y-4">
            {plan.pages.map((page) => (
              <li key={page.route}>
                <p className="text-[15px] font-medium text-ink">
                  {page.title} <span className="font-mono text-[12px] text-ink-faint">{page.route}</span>
                </p>
                <p className="text-[13px] text-ink-muted">{page.sections.join(" · ")}</p>
              </li>
            ))}
          </ul>
          {plan.site_wide.length > 0 && (
            <p className="mt-4 text-[13px] text-ink-muted">On every page: {plan.site_wide.join(" · ")}</p>
          )}
        </Section>

        {plan.custom_parts.length > 0 && (
          <Section title="Built specially for you">
            <ul className="space-y-2 text-[15px] text-ink">
              {plan.custom_parts.map((part) => (
                <li key={part.name}>
                  <span className="font-medium">{part.name}</span>
                  <span className="text-ink-muted"> · {part.purpose}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {plan.stored.length > 0 && (
          <Section title="In your project dashboard">
            <ul className="space-y-2 text-[15px] text-ink">
              {plan.stored.map((view) => (
                <li key={view.title}>
                  <span className="font-medium">{view.title}</span>
                  <span className="text-ink-muted"> · {view.columns.join(", ")}</span>
                  {view.statuses.length > 0 && (
                    <span className="block text-[13px] text-ink-faint">{view.statuses.join(" → ")}</span>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {plan.details_needed.length > 0 && (
          <Section title="Details we'll ask you for">
            <p className="text-[15px] text-ink">{plan.details_needed.join(", ")}</p>
          </Section>
        )}

        {plan.not_built.length > 0 && (
          <Section title="Not included">
            <ul className="space-y-1.5 text-[15px] text-ink">
              {plan.not_built.map((n) => (
                <li key={n.asked}>
                  {n.asked}
                  <span className="text-ink-muted"> · {n.alternative || n.reason}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {plan.assumptions.length > 0 && (
          <Section title="Choices we made for you">
            <ul className="list-disc space-y-1 pl-5 text-[15px] text-ink">
              {plan.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </Section>
        )}
      </div>

      {editing && (
        <div className="mt-2">
          <label htmlFor="plan-change" className="text-[13px] font-medium text-ink-muted">
            What should change? (one change)
          </label>
          <textarea
            id="plan-change"
            autoFocus
            rows={3}
            maxLength={500}
            value={changeText}
            disabled={busy}
            onChange={(e) => setChangeText(e.target.value)}
            placeholder="For example: use a photo grid instead of a slideshow."
            className="mt-2 block w-full resize-none rounded-lg border border-line bg-surface px-4 py-3 text-[15px] text-ink placeholder:text-ink-faint focus:border-ember/60 focus:outline-none"
          />
        </div>
      )}

      {error && (
        <p role="alert" className="mt-5 rounded-lg bg-alert-soft px-4 py-3 text-[14px] text-alert">
          {error}
        </p>
      )}

      <div className="sticky bottom-0 z-10 -mx-5 mt-8 flex flex-wrap items-center gap-x-5 gap-y-3 border-t border-line bg-paper/95 px-5 py-4 backdrop-blur-sm sm:-mx-8 sm:px-8">
        {approved ? (
          <>
            <p className="text-[13px] text-ink-muted">Building your site is the next step.</p>
            <button type="button" onClick={onStartOver} className={`ml-auto ${linkButton}`}>
              Start over
            </button>
          </>
        ) : editing ? (
          <>
            <button
              type="button"
              disabled={busy || changeText.trim().length === 0}
              onClick={() => onDecide({ decision: "change", change_text: changeText.trim() })}
              className="rounded-lg bg-ink px-5 py-2.5 text-[14px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:cursor-not-allowed disabled:bg-surface-sunk disabled:text-ink-faint"
            >
              Apply change
            </button>
            <button type="button" disabled={busy} onClick={() => setEditing(false)} className={linkButton}>
              Back to plan
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDecide({ decision: "approve" })}
              className="rounded-lg bg-ember px-5 py-2.5 text-[14px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:opacity-50"
            >
              Approve plan
            </button>
            {plan.changes_left > 0 && (
              <button
                type="button"
                disabled={busy}
                onClick={() => setEditing(true)}
                className="rounded-lg border border-line px-4 py-2.5 text-[14px] font-medium text-ink transition-colors duration-200 hover:border-ink-faint hover:bg-surface"
              >
                Change something
              </button>
            )}
            <span className="ml-auto flex items-center gap-3">
              {cancelArmed ? (
                <>
                  <span className="text-[13px] text-ink-muted">Cancel this website?</span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onDecide({ decision: "cancel" })}
                    className="text-[13px] font-medium text-alert hover:underline"
                  >
                    Yes, cancel
                  </button>
                  <button type="button" onClick={() => setCancelArmed(false)} className="text-[13px] font-medium text-ink-muted hover:text-ink">
                    Keep it
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setCancelArmed(true)}
                  className="text-[13px] font-medium text-ink-faint transition-colors duration-200 hover:text-ink"
                >
                  Cancel
                </button>
              )}
            </span>
          </>
        )}
      </div>
    </section>
  );
}
