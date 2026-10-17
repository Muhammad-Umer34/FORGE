// D:\FYP\FORGE-1\frontend\src\components\clarification\ConfirmationPanel.tsx
"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import { ConfirmationData, ConfirmationDecision, FeatureSource, ImageColours } from "@/types/request";
import { ThemePicker } from "./ThemePicker";
import { ThemeSources } from "./ThemeSources";

const SOURCE_LABEL: Record<FeatureSource, string> = {
  user_stated: "You asked for this",
  user_confirmed: "From your answer",
  user_delegated: "Chosen for you",
  proposed_accepted: "Suggestion you added",
  baseline_default: "Included by default",
};

interface ConfirmationPanelProps {
  screen: ConfirmationData;
  busy: boolean;
  error: string | null;
  onDecide: (decision: ConfirmationDecision) => void;
  onReadImage: (kind: "logo" | "screenshot", file: File) => Promise<ImageColours>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line py-6">
      <h2 className="text-[13px] font-medium text-ink-muted">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Tick({ on }: { on: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-[5px] border transition-colors duration-200 ${
        on ? "border-ember bg-ember text-paper" : "border-line bg-paper"
      }`}
    >
      {on && <Check className="h-3.5 w-3.5" strokeWidth={3} />}
    </span>
  );
}

export function ConfirmationPanel({ screen, busy, error, onDecide, onReadImage }: ConfirmationPanelProps) {
  const [removedDefaults, setRemovedDefaults] = useState<string[]>([]);
  const [extras, setExtras] = useState<string[]>([]);
  const [themePick, setThemePick] = useState({ forScreen: screen.theme_selected, id: screen.theme_selected });
  const themeId = themePick.forScreen === screen.theme_selected ? themePick.id : screen.theme_selected;
  const setThemeId = (id: string) => setThemePick({ forScreen: screen.theme_selected, id });
  const selectedTheme = screen.themes.find((t) => t.id === themeId);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [cancelArmed, setCancelArmed] = useState(false);

  const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  const canEdit = screen.actions.includes("edit");

  return (
    <section aria-labelledby="confirm-title" className="animate-rise">
      <p className="text-[13px] font-medium text-ember-strong">Step 3 · Confirm</p>
      <h1
        id="confirm-title"
        className="mt-3 font-display text-[2.3rem] leading-[1.05] tracking-[-0.01em] text-ink sm:text-[2.9rem]"
      >
        Here&apos;s what FORGE will build.
      </h1>
      <p className="mt-5 max-w-[62ch] text-[16px] leading-relaxed text-ink">{screen.summary}</p>

      {screen.please_check.length > 0 && (
        <div className="mt-6 rounded-lg border-l-2 border-ember bg-ember-soft/60 px-4 py-3">
          <p className="text-[13px] font-medium text-ember-strong">Please check</p>
          <ul className="mt-1.5 space-y-1 text-[14px] text-ink">
            {screen.please_check.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-8">
        <Section title={`Pages (${screen.pages.length})`}>
          <ul className="flex flex-wrap gap-2">
            {screen.pages.map((page) => (
              <li key={page} className="rounded-md bg-surface-sunk px-3 py-1.5 text-[14px] capitalize text-ink">
                {page}
              </li>
            ))}
          </ul>
        </Section>

        <Section title="What your site will have">
          <ul className="divide-y divide-line">
            {screen.features.map((f) => {
              const kept = !removedDefaults.includes(f.id);
              const row = (
                <>
                  <span className="flex flex-col">
                    <span className={`text-[15px] ${kept ? "text-ink" : "text-ink-faint line-through"}`}>{f.name}</span>
                    <span className="text-[12px] text-ink-faint">{SOURCE_LABEL[f.source]}</span>
                  </span>
                  {f.can_untick ? <Tick on={kept} /> : <Check aria-hidden="true" className="h-4 w-4 text-positive" />}
                </>
              );
              return (
                <li key={f.id}>
                  {f.can_untick ? (
                    <button
                      type="button"
                      aria-pressed={kept}
                      aria-label={`${f.name}: ${kept ? "included, select to remove" : "removed, select to include"}`}
                      disabled={busy}
                      onClick={() => setRemovedDefaults((prev) => toggle(prev, f.id))}
                      className="flex w-full items-center justify-between gap-4 py-3 text-left transition-colors duration-200 hover:bg-surface-sunk/50"
                    >
                      {row}
                    </button>
                  ) : (
                    <div className="flex items-center justify-between gap-4 py-3">{row}</div>
                  )}
                </li>
              );
            })}
          </ul>
        </Section>

        {screen.extras.length > 0 && (
          <Section title="Suggestions you can add">
            <ul className="grid gap-2.5 sm:grid-cols-2">
              {screen.extras.map((e) => {
                const on = extras.includes(e.id);
                return (
                  <li key={e.id}>
                    <button
                      type="button"
                      aria-pressed={on}
                      aria-label={`Add ${e.name}`}
                      disabled={busy}
                      onClick={() => setExtras((prev) => toggle(prev, e.id))}
                      className={`flex h-full w-full items-start justify-between gap-3 rounded-lg border px-4 py-3 text-left transition-all duration-200 active:scale-[0.99] ${
                        on ? "border-ember bg-ember-soft" : "border-line bg-surface hover:border-ink-faint"
                      }`}
                    >
                      <span className="flex flex-col gap-0.5">
                        <span className="text-[15px] font-medium text-ink">{e.name}</span>
                        <span className="text-[12px] text-ink-muted">{e.reason}</span>
                      </span>
                      <Tick on={on} />
                    </button>
                  </li>
                );
              })}
            </ul>
          </Section>
        )}

        <Section title="Look and feel">
          <ThemePicker themes={screen.themes} selected={themeId} onSelect={setThemeId} disabled={busy} />
          {selectedTheme && selectedTheme.notes.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-[12px] text-ink-muted">
              {selectedTheme.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
          {screen.actions.includes("theme_source") && (
            <ThemeSources
              left={screen.theme_sources_left}
              notice={screen.theme_notice}
              busy={busy}
              onReadImage={onReadImage}
              onUse={(source) => onDecide({ decision: "theme_source", theme_source: source })}
            />
          )}
          <p className="mt-3 text-[12px] text-ink-faint">
            Every theme is checked so text stays easy to read (WCAG 2.2 AA), in light and dark mode.
          </p>
        </Section>

        {screen.limits_notice.length > 0 && (
          <Section title="Not included">
            <ul className="space-y-3">
              {screen.limits_notice.map((item) => (
                <li key={item.asked} className="rounded-lg bg-surface-sunk px-4 py-3">
                  <p className="text-[15px] font-medium text-ink">&ldquo;{item.asked}&rdquo;</p>
                  <p className="mt-1 text-[14px] text-ink-muted">{item.reason}</p>
                  {item.alternative && (
                    <p className="mt-1.5 text-[14px] text-ink">
                      <span className="font-medium">Instead: </span>
                      {item.alternative}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {screen.assumptions.length > 0 && (
          <Section title="We assumed">
            <ul className="space-y-1.5 text-[14px] text-ink">
              {screen.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </Section>
        )}

        <p className="border-t border-line pt-6 text-[14px] text-ink-muted">{screen.business_details_note}</p>
      </div>

      {editing && (
        <div className="mt-6">
          <label htmlFor="edit-text" className="text-[13px] font-medium text-ink-muted">
            What should change? ({screen.edits_left} {screen.edits_left === 1 ? "change" : "changes"} left)
          </label>
          <textarea
            id="edit-text"
            autoFocus
            rows={3}
            maxLength={500}
            value={editText}
            disabled={busy}
            onChange={(e) => setEditText(e.target.value)}
            placeholder="For example: add a photo gallery and remove the about page."
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
        {editing ? (
          <>
            <button
              type="button"
              disabled={busy || editText.trim().length === 0}
              onClick={() => onDecide({ decision: "edit", edit_text: editText.trim() })}
              className="rounded-lg bg-ink px-5 py-2.5 text-[14px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:cursor-not-allowed disabled:bg-surface-sunk disabled:text-ink-faint"
            >
              Apply change
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setEditing(false)}
              className="text-[14px] font-medium text-ink-muted transition-colors duration-200 hover:text-ink"
            >
              Back to summary
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                onDecide({ decision: "confirm", ticked_extra_ids: extras, unticked_default_ids: removedDefaults, theme_id: themeId })
              }
              className="rounded-lg bg-ember px-5 py-2.5 text-[14px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:opacity-50"
            >
              Confirm and continue
            </button>
            {canEdit && (
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
                  <span className="text-[13px] text-ink-muted">Cancel this request?</span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onDecide({ decision: "cancel" })}
                    className="text-[13px] font-medium text-alert hover:underline"
                  >
                    Yes, cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => setCancelArmed(false)}
                    className="text-[13px] font-medium text-ink-muted hover:text-ink"
                  >
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
