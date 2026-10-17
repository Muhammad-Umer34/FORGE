// D:\FYP\FORGE-1\frontend\src\components\clarification\ForgeStudio.tsx
"use client";

import { useEffect, useState } from "react";
import { ApiError, answerQuestion, confirmBrief, createRequest, getRequest, readImageColours } from "@/services/api";
import { ConfirmationDecision, ReplyData, RequestEnvelope, UserAnswer } from "@/types/request";
import { ConfirmationPanel } from "./ConfirmationPanel";
import { OutcomeView } from "./OutcomeView";
import { QuestionCard } from "./QuestionCard";
import { ComposerReply, RequestComposer } from "./RequestComposer";
import { Step, StudioHeader } from "./StudioHeader";

type Busy = "start" | "answer" | "confirm" | "restore" | "theme";

// Only the request id is kept in the browser; the run itself lives on the server (resumable).
const STORAGE_KEY = "forge_request_id";

// Live runs took roughly 4-13 s per step, so the wait shows what is happening.
const PROGRESS: Record<Busy, string[]> = {
  start: ["Reading your request", "Matching it to what FORGE can build", "Preparing your next step"],
  answer: ["Saving your answer", "Checking what is still missing"],
  confirm: ["Locking in your choices", "Writing the checks for your finished site", "Almost done"],
  restore: ["Picking up where you left off"],
  theme: ["Building your theme", "Reading the website's colours and fonts", "Checking every colour is easy to read"],
};

const storage = {
  get: () => {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  },
  set: (id: string) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* private mode: the request simply won't survive a reload */
    }
  },
  clear: () => {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* nothing to clear */
    }
  },
};

function ProgressNote({ busy }: { busy: Busy }) {
  const [index, setIndex] = useState(0);
  const messages = PROGRESS[busy];

  useEffect(() => {
    const timer = window.setInterval(() => setIndex((i) => Math.min(i + 1, messages.length - 1)), 3500);
    return () => window.clearInterval(timer);
  }, [messages.length]);

  return (
    <div role="status" aria-live="polite" className="mb-8 flex items-center gap-3 text-[14px] text-ink-muted">
      <span aria-hidden="true" className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-ember"
            style={{ animationDelay: `${i * 180}ms` }}
          />
        ))}
      </span>
      <span key={index} className="animate-rise">{messages[index]}…</span>
    </div>
  );
}

function stepFor(envelope: RequestEnvelope | null): Step {
  if (!envelope) return "describe";
  if (envelope.status === "needs_clarification") return "answer";
  if (envelope.status === "awaiting_confirmation") return "confirm";
  return "brief";
}

export default function ForgeStudio() {
  const [envelope, setEnvelope] = useState<RequestEnvelope | null>(null);
  const [busy, setBusy] = useState<Busy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState("");
  const [reply, setReply] = useState<ComposerReply | null>(null);
  const [composerKey, setComposerKey] = useState(0);

  const run = async (kind: Busy, call: () => Promise<RequestEnvelope>, said?: string) => {
    setBusy(kind);
    setError(null);
    try {
      const next = await call();
      if (next.status === "reply") {
        // Not a website request: answer on the start screen; no run to resume (D-150).
        setReply({ said: said ?? "", data: next.data as ReplyData });
        setEnvelope(null);
        setLastPrompt("");
        setComposerKey((k) => k + 1);
        storage.clear();
        return;
      }
      setReply(null);
      setEnvelope(next);
      storage.set(next.request_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  // Resume a request that was in progress before the page was reloaded.
  useEffect(() => {
    const saved = storage.get();
    if (!saved) return;
    let active = true;
    const restore = async () => {
      setBusy("restore");
      try {
        const env = await getRequest(saved);
        if (active) setEnvelope(env);
      } catch {
        storage.clear(); // unknown or expired request: start fresh
      } finally {
        if (active) setBusy(null);
      }
    };
    restore();
    return () => {
      active = false;
    };
  }, []);

  // Each new screen (question, confirmation, outcome) starts at the top of the page.
  const screenKey = envelope
    ? `${envelope.status}-${envelope.status === "needs_clarification" ? envelope.data.question_id : ""}`
    : "composer";
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [screenKey]);

  const startOver = () => {
    storage.clear();
    setEnvelope(null);
    setError(null);
    setLastPrompt(""); // a fresh start gets an empty box; the prompt is kept only for "Try again"
    setReply(null);
  };

  const start = (prompt: string) => {
    setLastPrompt(prompt);
    run("start", () => createRequest(prompt), prompt);
  };

  const answer = (a: UserAnswer) => {
    if (envelope) run("answer", () => answerQuestion(envelope.request_id, a));
  };

  const decide = (d: ConfirmationDecision) => {
    const kind: Busy = d.decision === "confirm" ? "confirm" : d.decision === "theme_source" ? "theme" : "answer";
    if (envelope) run(kind, () => confirmBrief(envelope.request_id, d));
  };

  const readImage = (kind: "logo" | "screenshot", file: File) => {
    if (!envelope) return Promise.reject(new Error("No request is open."));
    return readImageColours(envelope.request_id, kind, file);
  };

  return (
    <>
      <StudioHeader step={stepFor(envelope)} onStartOver={envelope ? startOver : undefined} busy={busy !== null} />

      <main id="main" className="relative z-[1] mx-auto w-full max-w-3xl flex-1 px-5 pt-12 pb-16 sm:px-8 sm:pt-16">
        {busy && <ProgressNote key={busy} busy={busy} />}

        <div aria-busy={busy !== null} className={busy ? "pointer-events-none opacity-50 transition-opacity duration-300" : "transition-opacity duration-300"}>
          {!envelope && (
            <RequestComposer
              key={composerKey}
              onSubmit={start}
              busy={busy !== null}
              error={error}
              initialText={lastPrompt}
              reply={reply}
            />
          )}

          {envelope?.status === "needs_clarification" && (
            <QuestionCard key={envelope.data.question_id} question={envelope.data} busy={busy !== null} error={error} onAnswer={answer} />
          )}

          {envelope?.status === "awaiting_confirmation" && (
            <ConfirmationPanel
              key={`${envelope.request_id}-${envelope.data.edits_left}`}
              screen={envelope.data}
              busy={busy !== null}
              error={error}
              onDecide={decide}
              onReadImage={readImage}
            />
          )}

          {envelope &&
            (envelope.status === "complete" ||
              envelope.status === "out_of_scope" ||
              envelope.status === "failed" ||
              envelope.status === "cancelled") && (
              <OutcomeView
                outcome={envelope}
                onStartOver={startOver}
                onRetry={lastPrompt ? () => start(lastPrompt) : undefined}
              />
            )}
        </div>
      </main>

      <footer className="relative z-[1] border-t border-line/70">
        <div className="mx-auto max-w-5xl px-5 py-5 text-[12px] text-ink-faint sm:px-8">
          FORGE builds small-to-medium websites. Payments, logins and online stores with checkout are not supported yet.
        </div>
      </footer>
    </>
  );
}
