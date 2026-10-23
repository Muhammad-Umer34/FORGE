// D:\FYP\FORGE-1\frontend\src\components\clarification\ForgeStudio.tsx
"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/services/client";
import { listRequests } from "@/services/projects";
import { answerQuestion, cancelRequest, confirmBrief, createRequest, getRequest, readImageColours, resumeRequest } from "@/services/requests";
import { RequestSummary } from "@/types/auth";
import { ConfirmationDecision, ReplyData, RequestEnvelope, UserAnswer } from "@/types/request";
import { ConfirmationPanel } from "./ConfirmationPanel";
import { OutcomeView, StoppedView } from "./OutcomeView";
import { QuestionCard } from "./QuestionCard";
import { ComposerReply, RequestComposer } from "./RequestComposer";
import { RequestHistory } from "./RequestHistory";
import { StartOverDialog } from "./StartOverDialog";
import { Step, StudioHeader } from "./StudioHeader";

type Busy = "start" | "answer" | "confirm" | "restore" | "theme";

// Live runs took roughly 4-13 s per step, so the wait shows what is happening.
const PROGRESS: Record<Busy, string[]> = {
  start: ["Reading your request", "Matching it to what FORGE can build", "Preparing your next step"],
  answer: ["Saving your answer", "Checking what is still missing"],
  confirm: ["Locking in your choices", "Writing the checks for your finished site", "Almost done"],
  restore: ["Picking up where you left off"],
  theme: ["Building your theme", "Reading the website's colours and fonts", "Checking every colour is easy to read"],
};

// One project = one website (D-200): its current request is the latest one, unless that one ended
// without a website. The server's list decides, so any browser or device opens the same screen.
const ACTIVE: ReadonlyArray<RequestSummary["status"]> = ["processing", "needs_clarification", "awaiting_confirmation", "complete", "paused"];

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

interface ForgeStudioProps {
  projectId: string;
  projectName: string;
}

export default function ForgeStudio({ projectId, projectName }: ForgeStudioProps) {
  const [history, setHistory] = useState<RequestSummary[]>([]);
  const [envelope, setEnvelope] = useState<RequestEnvelope | null>(null);
  const [busy, setBusy] = useState<Busy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState("");
  const [reply, setReply] = useState<ComposerReply | null>(null);
  const [composerKey, setComposerKey] = useState(0);
  const [confirmingStartOver, setConfirmingStartOver] = useState(false);
  const openedCurrent = useRef(false);

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
        return;
      }
      setReply(null);
      setEnvelope(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  // The project's requests, shown under the composer; refreshed whenever it shows again. The first time,
  // the project's current request (newest first) is opened instead of an empty composer.
  useEffect(() => {
    if (envelope) return;
    let active = true;
    // the list is a convenience: if it fails, the composer simply shows without it
    listRequests(projectId).catch((): RequestSummary[] => []).then(async (list) => {
      if (!active) return;
      setHistory(list);
      if (openedCurrent.current) return;
      openedCurrent.current = true;
      const current = list[0];
      if (!current || !ACTIVE.includes(current.status)) return;
      setBusy("restore");
      try {
        const env = await getRequest(projectId, current.id);
        if (active) setEnvelope(env);
      } catch {
        /* deleted meanwhile, or not ours: the composer stays */
      } finally {
        if (active) setBusy(null);
      }
    });
    return () => {
      active = false;
    };
  }, [envelope, projectId]);

  const openRequest = (requestId: string) =>
    run("restore", () => getRequest(projectId, requestId));

  // Each new screen (question, confirmation, outcome) starts at the top of the page.
  const screenKey = envelope
    ? `${envelope.status}-${envelope.status === "needs_clarification" ? envelope.data.question_id : ""}`
    : "composer";
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [screenKey]);

  // Back to the composer. Only for a request that ended without a website; otherwise ask first.
  const startOver = () => {
    setEnvelope(null);
    setError(null);
    setLastPrompt(""); // a fresh start gets an empty box; the prompt is kept only for "Try again"
    setReply(null);
  };

  const requestStartOver = () => {
    if (envelope && ACTIVE.includes(envelope.status as RequestSummary["status"])) setConfirmingStartOver(true);
    else startOver();
  };

  const confirmStartOver = async () => {
    if (envelope) await cancelRequest(projectId, envelope.request_id); // errors are shown in the dialog
    setConfirmingStartOver(false);
    startOver();
  };

  const start = (prompt: string) => {
    setLastPrompt(prompt);
    run("start", () => createRequest(projectId, prompt), prompt);
  };

  const answer = (a: UserAnswer) => {
    if (envelope) run("answer", () => answerQuestion(projectId, envelope.request_id, a));
  };

  const decide = (d: ConfirmationDecision) => {
    const kind: Busy = d.decision === "confirm" ? "confirm" : d.decision === "theme_source" ? "theme" : "answer";
    if (envelope) run(kind, () => confirmBrief(projectId, envelope.request_id, d));
  };

  const resume = () => {
    if (envelope) run("restore", () => resumeRequest(projectId, envelope.request_id));
  };

  const cancel = () => {
    if (envelope) run("answer", () => cancelRequest(projectId, envelope.request_id));
  };

  const readImage = (kind: "logo" | "screenshot", file: File) => {
    if (!envelope) return Promise.reject(new Error("No request is open."));
    return readImageColours(projectId, envelope.request_id, kind, file);
  };

  return (
    <>
      <StudioHeader
        step={stepFor(envelope)}
        projectName={projectName}
        onStartOver={envelope && envelope.status !== "processing" ? requestStartOver : undefined}
        busy={busy !== null}
      />

      <main id="main" className="relative z-[1] mx-auto w-full max-w-3xl flex-1 px-5 pt-12 pb-16 sm:px-8 sm:pt-16">
        {busy && <ProgressNote key={busy} busy={busy} />}

        <div aria-busy={busy !== null} className={busy ? "pointer-events-none opacity-50 transition-opacity duration-300" : "transition-opacity duration-300"}>
          {!envelope && (
            <>
              <RequestComposer
                key={composerKey}
                onSubmit={start}
                busy={busy !== null}
                error={error}
                initialText={lastPrompt}
                reply={reply}
              />
              {history.length > 0 && (
                <p className="mt-4 text-[14px] text-ink-muted">
                  Building a different website?{" "}
                  <Link href="/projects" className="font-medium text-ember-strong underline-offset-2 hover:underline">
                    Create a new project
                  </Link>
                  .
                </p>
              )}
              <RequestHistory requests={history} onOpen={openRequest} busy={busy !== null} />
            </>
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

          {(envelope?.status === "paused" || envelope?.status === "processing") && (
            <StoppedView
              run={envelope}
              onContinue={resume}
              onCancel={cancel}
              onCheckAgain={() => openRequest(envelope.request_id)}
            />
          )}

          {envelope &&
            (envelope.status === "complete" ||
              envelope.status === "out_of_scope" ||
              envelope.status === "failed" ||
              envelope.status === "cancelled") && (
              <OutcomeView
                outcome={envelope}
                onStartOver={requestStartOver}
                onRetry={lastPrompt ? () => start(lastPrompt) : undefined}
              />
            )}
        </div>
      </main>

      {confirmingStartOver && (
        <StartOverDialog onKeep={() => setConfirmingStartOver(false)} onStartOver={confirmStartOver} />
      )}

      <footer className="relative z-[1] border-t border-line/70">
        <div className="mx-auto max-w-5xl px-5 py-5 text-[12px] text-ink-faint sm:px-8">
          FORGE builds small-to-medium websites. Payments, logins and online stores with checkout are not supported yet.
        </div>
      </footer>
    </>
  );
}
