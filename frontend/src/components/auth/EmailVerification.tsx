// D:\FYP\FORGE-1\frontend\src\components\auth\EmailVerification.tsx
"use client";

// Email verification (D-185, D-188): the page the emailed link opens, and the banner shown to
// signed-in users who have not verified yet. Unverified users can sign in but cannot create
// projects or run requests; the backend enforces this, these screens explain it.

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ApiError } from "@/services/client";
import * as authApi from "@/services/auth";
import { useAuth } from "./AuthProvider";
import { AuthShell, Notice, authButtonClass } from "./AuthShell";

type State = "verifying" | "verified" | "done" | "failed";

export function VerifyEmailScreen() {
  const token = useSearchParams().get("token") ?? "";
  const { status, reloadSession } = useAuth();
  const [state, setState] = useState<State>(token ? "verifying" : "failed");
  const [error, setError] = useState(token ? "" : "This link is missing its code. Please open the link from the email again.");
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return; // a link works once, so it is sent once
    started.current = true;
    authApi
      .verifyEmail(token)
      .then(() => setState("verified"))
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
        setState("failed");
      });
  }, [token]);

  // A signed-in user first gets a fresh access token that says the email is verified, so the next
  // page already allows projects. Waiting for the sign-in check means this refresh starts after
  // the verification, never before it.
  useEffect(() => {
    if (state !== "verified" || status === "loading") return;
    if (status === "signed_in") reloadSession().finally(() => setState("done"));
    else setState("done"); // eslint-disable-line react-hooks/set-state-in-effect -- reacts to the sign-in check
  }, [state, status, reloadSession]);

  if (state === "verifying" || state === "verified") return <AuthShell title="Verifying your email" lead="One moment…">{null}</AuthShell>;

  if (state === "done") {
    return (
      <AuthShell title="Email verified" lead="Thank you. You can now create projects and describe your websites.">
        <Link href={status === "signed_in" ? "/projects" : "/login"} className={`${authButtonClass} block text-center`}>
          {status === "signed_in" ? "Go to your projects" : "Sign in"}
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="This link did not work" lead="Verification links work once and expire after 24 hours.">
      <div className="space-y-5">
        <Notice tone="error">{error}</Notice>
        <Link href={status === "signed_in" ? "/projects" : "/login"} className={`${authButtonClass} block text-center`}>
          {status === "signed_in" ? "Back to your projects to send a new link" : "Sign in to send a new link"}
        </Link>
      </div>
    </AuthShell>
  );
}

/** Shown on signed-in pages until the email is verified. */
export function VerifyEmailBanner() {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ tone: "error" | "success"; text: string } | null>(null);
  if (!user || user.email_verified) return null;

  const resend = async () => {
    setBusy(true);
    setNote(null);
    try {
      const result = await authApi.resendVerification();
      setNote({ tone: "success", text: result.message });
    } catch (err) {
      setNote({ tone: "error", text: err instanceof ApiError ? err.message : "The email could not be sent. Please try again." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="verify-title" className="mb-8 rounded-2xl border border-ember/30 bg-ember-soft px-5 py-4">
      <h2 id="verify-title" className="text-[15px] font-semibold text-ember-strong">Verify your email to start building</h2>
      <p className="mt-1 text-[14px] text-ink">
        We sent a link to <span className="font-medium">{user.email}</span>. Open it to create projects and describe your websites.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={resend}
          disabled={busy}
          className="rounded-lg bg-ink px-3.5 py-2 text-[13px] font-medium text-paper hover:opacity-90 disabled:opacity-40"
        >
          {busy ? "Sending…" : "Send the link again"}
        </button>
        {note && <span role="status" className={`text-[13px] ${note.tone === "error" ? "text-alert" : "text-positive"}`}>{note.text}</span>}
      </div>
    </section>
  );
}
