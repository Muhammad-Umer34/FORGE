// D:\FYP\FORGE-1\frontend\src\components\auth\AuthForm.tsx
"use client";

// Sign-in and create-account form (D-181). Messages come from the backend, which gives the same
// answer for an unknown email and a wrong password.

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError } from "@/services/client";
import { ForgeMark } from "@/components/clarification/StudioHeader";
import { useAuth } from "./AuthProvider";
import { PageLoading, safeNextPath } from "./RequireAuth";

const MIN_PASSWORD = 8; // same as backend/models/auth.py (NIST SP 800-63B)

interface AuthFormProps {
  mode: "login" | "register";
}

const COPY = {
  login: {
    title: "Welcome back",
    lead: "Sign in to continue with your website projects.",
    submit: "Sign in",
    busy: "Signing in",
    switchText: "New to FORGE?",
    switchLink: "Create an account",
    switchHref: "/register",
  },
  register: {
    title: "Create your account",
    lead: "Describe your website in plain words. FORGE asks a few quick questions and plans the build.",
    submit: "Create account",
    busy: "Creating your account",
    switchText: "Already have an account?",
    switchLink: "Sign in",
    switchHref: "/login",
  },
} as const;

const fieldClass =
  "mt-1.5 block w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint " +
  "transition-colors duration-200 focus:border-ember focus:outline-none focus:ring-2 focus:ring-ember/25";

export function AuthForm({ mode }: AuthFormProps) {
  const copy = COPY[mode];
  const { status, login, register } = useAuth();
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next"));

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "signed_in") router.replace(next);
  }, [status, router, next]);

  if (status !== "signed_out") return <PageLoading label={status === "loading" ? "Checking your sign-in" : "Opening your projects"} />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    if (mode === "register" && password.length < MIN_PASSWORD) {
      setError(`Please use at least ${MIN_PASSWORD} characters for your password.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email.trim(), password);
      else await register(email.trim(), password, name.trim());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setBusy(false);
    }
  };

  const switchHref = next === "/projects" ? copy.switchHref : `${copy.switchHref}?next=${encodeURIComponent(next)}`;

  return (
    <main id="main" className="flex flex-1 items-center justify-center px-5 py-12 sm:px-8">
      <div className="w-full max-w-sm animate-rise">
        <div className="mb-8 flex items-center gap-2.5">
          <ForgeMark />
          <span className="text-[15px] font-semibold tracking-[0.18em] text-ink">FORGE</span>
        </div>

        <h1 className="font-display text-[38px] leading-[1.1] text-ink">{copy.title}</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">{copy.lead}</p>

        <form onSubmit={submit} noValidate className="mt-8 space-y-5">
          {mode === "register" && (
            <label className="block text-[14px] font-medium text-ink">
              Your name
              <input
                className={fieldClass}
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                maxLength={80}
                required
              />
            </label>
          )}

          <label className="block text-[14px] font-medium text-ink">
            Email
            <input
              className={fieldClass}
              type="email"
              inputMode="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              spellCheck={false}
              required
            />
          </label>

          <div>
            <div className="flex items-baseline justify-between">
              <label className="block text-[14px] font-medium text-ink" htmlFor="password">
                Password
              </label>
              {mode === "login" && (
                <Link href="/forgot-password" className="text-[13px] font-medium text-ember-strong underline-offset-4 hover:underline">
                  Forgot password?
                </Link>
              )}
            </div>
            <div className="relative">
              <input
                id="password"
                className={`${fieldClass} pr-20`}
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                aria-describedby={mode === "register" ? "password-hint" : undefined}
                maxLength={128}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-1.5 my-1.5 rounded-md px-2.5 text-[13px] font-medium text-ink-muted hover:bg-surface-sunk hover:text-ink"
                aria-pressed={showPassword}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            {mode === "register" && (
              <p id="password-hint" className="mt-1.5 text-[13px] text-ink-faint">
                At least {MIN_PASSWORD} characters. A short sentence works well.
              </p>
            )}
          </div>

          {error && (
            <p role="alert" className="rounded-lg bg-alert-soft px-3.5 py-2.5 text-[14px] text-alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !email.trim() || !password || (mode === "register" && !name.trim())}
            className="w-full rounded-lg bg-ink px-4 py-3 text-[15px] font-medium text-paper transition-opacity duration-200 hover:opacity-90 disabled:opacity-40"
          >
            {busy ? `${copy.busy}…` : copy.submit}
          </button>
        </form>

        <p className="mt-6 text-[14px] text-ink-muted">
          {copy.switchText}{" "}
          <Link href={switchHref} className="font-medium text-ember-strong underline-offset-4 hover:underline">
            {copy.switchLink}
          </Link>
        </p>
      </div>
    </main>
  );
}
