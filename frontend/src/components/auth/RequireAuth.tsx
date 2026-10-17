// D:\FYP\FORGE-1\frontend\src\components\auth\RequireAuth.tsx
"use client";

// Page guard (D-181). The real protection is on the backend: every projects and requests call needs
// a valid access token. This only sends signed-out visitors to the sign-in page, and back afterwards.

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

export function PageLoading({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex flex-1 items-center justify-center py-24 text-[14px] text-ink-muted">
      <span aria-hidden="true" className="mr-3 flex gap-1">
        {[0, 1, 2].map((i) => (
          <span key={i} className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-ember" style={{ animationDelay: `${i * 180}ms` }} />
        ))}
      </span>
      {label}…
    </div>
  );
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status, signedOutByUser } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status !== "signed_out") return;
    // After "Sign out" there is nothing to come back to (the next person may use another account).
    // Otherwise remember the page; the address is read only here, so the shell can be prerendered.
    router.replace(signedOutByUser ? "/login" : `/login?next=${encodeURIComponent(window.location.pathname)}`);
  }, [status, signedOutByUser, router]);

  if (status !== "signed_in") return <PageLoading label={status === "loading" ? "Checking your sign-in" : "Opening sign-in"} />;
  return <>{children}</>;
}

/** "/" has no page of its own: signed-in users go to their projects, others to sign-in. */
export function HomeRedirect() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status !== "loading") router.replace(status === "signed_in" ? "/projects" : "/login");
  }, [status, router]);

  return <PageLoading />;
}

/** Only same-site paths are allowed after sign-in, so a link can't send users to another website. */
export function safeNextPath(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/\\") ? next : "/projects";
}
