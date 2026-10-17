// D:\FYP\FORGE-1\frontend\src\components\clarification\RequestComposer.tsx
"use client";

import { useState } from "react";

const MAX_CHARS = 2000; // same cap as the agent's input sanitiser
const MIN_CHARS = 10;

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
}

export function RequestComposer({ onSubmit, busy, error, initialText = "" }: RequestComposerProps) {
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
          <p className="mt-2 text-[13px] text-alert">Add a little more detail: what is the website for?</p>
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
