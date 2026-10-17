// D:\FYP\FORGE-1\frontend\src\components\clarification\RequestComposer.tsx
"use client";

import { useState } from "react";
import { ReplyData } from "@/types/request";

const MAX_CHARS = 2000; // same cap as the agent's input sanitiser
const MIN_CHARS = 2; // short messages like "hi" get a reply too (D-150)

/** FORGE's answer to a message that was not a website request, with what the user said. */
export interface ComposerReply {
  said: string;
  data: ReplyData;
}

const EXAMPLES = [
  "A website for my bakery with our cake menu, pre-order requests and a map to the shop.",
  "A site for my hair salon where clients can book appointments and see our prices.",
  "A portfolio for my interior design work, with a short about section and a contact form.",
];

interface RequestComposerProps {
  onSubmit: (prompt: string) => void;
  busy: boolean;
  error: string | null;
  initialText?: string;
  reply?: ComposerReply | null;
}

export function RequestComposer({ onSubmit, busy, error, initialText = "", reply = null }: RequestComposerProps) {
  const [text, setText] = useState(initialText);
  const [touched, setTouched] = useState(false);
  const trimmed = text.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_CHARS;

  const submit = () => {
    setTouched(true);
    if (busy || trimmed.length < MIN_CHARS) return;
    onSubmit(trimmed);
  };

  return (
    <section aria-labelledby="composer-title" className="animate-rise">
      <p className="text-[13px] font-medium text-ember-strong">Step 1 · Describe</p>
      <h1
        id="composer-title"
        className="mt-3 max-w-[16ch] font-display text-[2.6rem] leading-[1.02] tracking-[-0.01em] text-ink sm:text-[3.4rem]"
      >
        Describe the website you need.
      </h1>
      <p className="mt-4 max-w-[58ch] text-[15px] leading-relaxed text-ink-muted">
        Write it the way you would tell a friend. If something is missing, FORGE asks a few quick
        questions, then shows you a summary to confirm before anything is built.
      </p>

      {reply && (
        <div role="status" aria-live="polite" className="mt-8 animate-rise space-y-3">
          {reply.said && (
            <p className="ml-auto w-fit max-w-[85%] rounded-lg bg-surface-sunk px-4 py-2.5 text-[15px] text-ink">
              <span className="sr-only">You said: </span>
              {reply.said}
            </p>
          )}
          <div className="max-w-[62ch] rounded-lg border-l-2 border-ember bg-surface px-4 py-3 shadow-card">
            <p className="text-[12px] font-semibold tracking-[0.14em] text-ember-strong">FORGE</p>
            <p className="mt-1 text-[15px] leading-relaxed text-ink">{reply.data.message}</p>
          </div>
        </div>
      )}

      <form
        className="mt-8"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor="prompt" className="sr-only">
          Your website request
        </label>
        <div className="rounded-xl border border-line bg-surface shadow-card transition-colors duration-200 focus-within:border-ember/60">
          <textarea
            id="prompt"
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                submit();
              }
            }}
            rows={5}
            disabled={busy}
            aria-invalid={touched && (tooShort || trimmed.length === 0)}
            aria-describedby="prompt-help"
            placeholder="For example: a website for my dental clinic with our services, opening hours and online appointment requests."
            className="block w-full resize-none rounded-xl bg-transparent px-5 pt-4 pb-2 text-[16px] leading-relaxed text-ink placeholder:text-ink-faint focus:outline-none disabled:opacity-60"
          />
          <div className="flex items-center justify-between gap-4 px-5 pt-1 pb-4">
            <span id="prompt-help" className="text-[12px] tabular-nums text-ink-faint">
              {text.length}/{MAX_CHARS} · Ctrl + Enter to start
            </span>
            <button
              type="submit"
              disabled={busy || trimmed.length < MIN_CHARS}
              className="rounded-lg bg-ink px-5 py-2.5 text-[14px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:cursor-not-allowed disabled:bg-surface-sunk disabled:text-ink-faint"
            >
              Start
            </button>
          </div>
        </div>
        {touched && tooShort && (
          <p className="mt-2 text-[13px] text-alert">Type a little more so FORGE can help.</p>
        )}
        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-alert-soft px-4 py-3 text-[14px] text-alert">
            {error}
          </p>
        )}
      </form>

      <div className="mt-10">
        <h2 className="text-[13px] font-medium text-ink-muted">Or start from an example</h2>
        <ul className="mt-3 divide-y divide-line border-y border-line">
          {EXAMPLES.map((example) => (
            <li key={example}>
              <button
                type="button"
                aria-label={`Use example: ${example}`}
                disabled={busy}
                onClick={() => setText(example)}
                className="group flex w-full items-baseline gap-3 py-3.5 text-left text-[15px] text-ink transition-colors duration-200 hover:text-ember-strong disabled:opacity-50"
              >
                <span aria-hidden="true" className="text-ink-faint transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-ember">
                  →
                </span>
                <span>{example}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
