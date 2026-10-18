// D:\FYP\FORGE-1\frontend\src\components\auth\PasswordReset.tsx
"use client";

// Forgot password and reset password (D-186). The backend gives the same answer whether or not an
// account exists, so this page never says which emails are registered.

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ApiError } from "@/services/client";
import * as authApi from "@/services/auth";
import { AuthShell, Notice, authButtonClass, authFieldClass } from "./AuthShell";

const MIN_PASSWORD = 8; // same as backend/models/auth.py

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || !email.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setSent((await authApi.forgotPassword(email.trim())).message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Forgot your password?" lead="Enter your email and we will send you a link to choose a new password.">
      {sent ? (
        <div className="space-y-5">
          <Notice tone="success">{sent}</Notice>
          <p className="text-[14px] text-ink-muted">Remember to check your spam folder.</p>
          <Link href="/login" className={`${authButtonClass} block text-center`}>Back to sign in</Link>
        </div>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <label className="block text-[14px] font-medium text-ink">
            Email
            <input className={authFieldClass} type="email" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)}
              autoComplete="email" spellCheck={false} required />
          </label>
          {error && <Notice tone="error">{error}</Notice>}
          <button type="submit" disabled={busy || !email.trim()} className={authButtonClass}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
          <p className="text-[14px] text-ink-muted">
            <Link href="/login" className="font-medium text-ember-strong underline-offset-4 hover:underline">Back to sign in</Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(token ? null : "This link is missing its code. Please open the link from the email again.");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || !token) return;
    if (password.length < MIN_PASSWORD) {
      setError(`Please use at least ${MIN_PASSWORD} characters.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setDone((await authApi.resetPassword(token, password)).message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <AuthShell title="Password changed" lead="For your safety, you have been signed out on every device.">
        <div className="space-y-5">
          <Notice tone="success">{done}</Notice>
          <Link href="/login" className={`${authButtonClass} block text-center`}>Sign in</Link>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Choose a new password" lead="Reset links work once and expire after 30 minutes.">
      <form onSubmit={submit} noValidate className="space-y-5">
        <div>
          <label className="block text-[14px] font-medium text-ink" htmlFor="new-password">New password</label>
          <div className="relative">
            <input id="new-password" className={`${authFieldClass} pr-20`} type={show ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" aria-describedby="new-password-hint"
              maxLength={128} required disabled={!token} />
            <button type="button" onClick={() => setShow((v) => !v)} aria-pressed={show}
              className="absolute inset-y-0 right-1.5 my-1.5 rounded-md px-2.5 text-[13px] font-medium text-ink-muted hover:bg-surface-sunk hover:text-ink">
              {show ? "Hide" : "Show"}
            </button>
          </div>
          <p id="new-password-hint" className="mt-1.5 text-[13px] text-ink-faint">At least {MIN_PASSWORD} characters. A short sentence works well.</p>
        </div>
        {error && <Notice tone="error">{error}</Notice>}
        <button type="submit" disabled={busy || !token || !password} className={authButtonClass}>
          {busy ? "Saving…" : "Save new password"}
        </button>
        <p className="text-[14px] text-ink-muted">
          <Link href="/forgot-password" className="font-medium text-ember-strong underline-offset-4 hover:underline">Ask for a new link</Link>
        </p>
      </form>
    </AuthShell>
  );
}
