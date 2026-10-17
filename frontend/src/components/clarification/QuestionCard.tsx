// D:\FYP\FORGE-1\frontend\src\components\clarification\QuestionCard.tsx
"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import { QuestionData, UserAnswer } from "@/types/request";

interface QuestionCardProps {
  question: QuestionData;
  busy: boolean;
  error: string | null;
  onAnswer: (answer: UserAnswer) => void;
}

/** One question per screen (decision D-104). Render it with key={question_id} so state resets. */
export function QuestionCard({ question, busy, error, onAnswer }: QuestionCardProps) {
  const [selected, setSelected] = useState<string[]>([]);
  const [writing, setWriting] = useState(false);
  const [text, setText] = useState("");

  const limit = question.multi_select ? question.max_selections ?? question.options.length : 1;
  const atLimit = question.multi_select && selected.length >= limit;

  const toggle = (id: string) => {
    if (busy) return;
    setWriting(false);
    if (!question.multi_select) {
      setSelected([id]);
      return;
    }
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length >= limit ? prev : [...prev, id],
    );
  };

  const canContinue = writing ? text.trim().length > 0 : selected.length > 0;

  const submit = () => {
    if (!canContinue || busy) return;
    onAnswer(
      writing
        ? { question_id: question.question_id, kind: "other", text: text.trim() }
        : { question_id: question.question_id, kind: "option", option_ids: selected },
    );
  };

  return (
    <section aria-labelledby="question-title" className="animate-rise">
      <p className="text-[13px] font-medium text-ember-strong">
        Question {question.number}
        <span className="text-ink-faint"> of up to {question.max_questions}</span>
      </p>
      <h1
        id="question-title"
        className="mt-3 max-w-[24ch] font-display text-[2.1rem] leading-[1.08] tracking-[-0.01em] text-ink sm:text-[2.6rem]"
      >
        {question.text}
      </h1>
      {question.multi_select && (
        <p className="mt-3 text-[14px] text-ink-muted">
          {question.max_selections ? `Choose up to ${question.max_selections}.` : "Choose all that apply."}
        </p>
      )}

      <div
        role="group"
        aria-labelledby="question-title"
        className="mt-7 grid gap-2.5 sm:grid-cols-2"
      >
        {question.options.map((option, i) => {
          const isOn = selected.includes(option.option_id);
          const blocked = !isOn && atLimit;
          return (
            <button
              key={option.option_id}
              type="button"
              aria-pressed={isOn}
              aria-label={option.recommended ? `${option.label} (recommended)` : option.label}
              disabled={busy || blocked}
              onClick={() => toggle(option.option_id)}
              style={{ animationDelay: `${60 + i * 45}ms` }}
              className={`group flex animate-rise items-start justify-between gap-3 rounded-lg border px-4 py-3.5 text-left transition-all duration-200 active:scale-[0.99] disabled:cursor-not-allowed ${
                isOn
                  ? "border-ember bg-ember-soft"
                  : "border-line bg-surface hover:border-ink-faint disabled:opacity-45"
              }`}
            >
              <span className="flex flex-col gap-1">
                <span className={`text-[15px] font-medium ${isOn ? "text-ember-strong" : "text-ink"}`}>
                  {option.label}
                </span>
                {option.recommended && (
                  <span className="text-[12px] text-ink-muted">Recommended</span>
                )}
              </span>
              <span
                aria-hidden="true"
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-[5px] border transition-colors duration-200 ${
                  isOn ? "border-ember bg-ember text-paper" : "border-line bg-paper"
                }`}
              >
                {isOn && <Check className="h-3.5 w-3.5" strokeWidth={3} />}
              </span>
            </button>
          );
        })}
      </div>

      {question.allow_other_text && (
        <div className="mt-4">
          {writing ? (
            <div>
              <label htmlFor="other-answer" className="text-[13px] font-medium text-ink-muted">
                Your answer
              </label>
              <textarea
                id="other-answer"
                autoFocus
                rows={3}
                maxLength={500}
                value={text}
                disabled={busy}
                onChange={(e) => setText(e.target.value)}
                className="mt-2 block w-full resize-none rounded-lg border border-line bg-surface px-4 py-3 text-[15px] text-ink placeholder:text-ink-faint focus:border-ember/60 focus:outline-none"
                placeholder="Say it in your own words."
              />
            </div>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setSelected([]);
                setWriting(true);
              }}
              className="text-[14px] text-ink-muted underline decoration-line underline-offset-4 transition-colors duration-200 hover:text-ink hover:decoration-ink-faint"
            >
              None of these fit, I&apos;ll type my own answer
            </button>
          )}
        </div>
      )}

      {error && (
        <p role="alert" className="mt-5 rounded-lg bg-alert-soft px-4 py-3 text-[14px] text-alert">
          {error}
        </p>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-line pt-6">
        <button
          type="button"
          onClick={submit}
          disabled={!canContinue || busy}
          className="rounded-lg bg-ink px-5 py-2.5 text-[14px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:cursor-not-allowed disabled:bg-surface-sunk disabled:text-ink-faint"
        >
          Continue
        </button>
        {question.allow_you_decide && (
          <button
            type="button"
            disabled={busy}
            onClick={() => onAnswer({ question_id: question.question_id, kind: "you_decide" })}
            className="text-[14px] font-medium text-ink-muted transition-colors duration-200 hover:text-ink disabled:opacity-50"
          >
            Let FORGE decide
          </button>
        )}
      </div>
    </section>
  );
}
