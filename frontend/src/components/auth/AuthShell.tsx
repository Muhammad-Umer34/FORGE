// D:\FYP\FORGE-1\frontend\src\components\auth\AuthShell.tsx
// The narrow, centred page used by the sign-in, email and password screens.

import { ReactNode } from "react";
import { ForgeMark } from "@/components/clarification/StudioHeader";

export const authFieldClass =
  "mt-1.5 block w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint " +
  "transition-colors duration-200 focus:border-ember focus:outline-none focus:ring-2 focus:ring-ember/25";

export const authButtonClass =
  "w-full rounded-lg bg-ink px-4 py-3 text-[15px] font-medium text-paper transition-opacity duration-200 hover:opacity-90 disabled:opacity-40";

export function AuthShell({ title, lead, children }: { title: string; lead?: ReactNode; children: ReactNode }) {
  return (
    <main id="main" className="flex flex-1 items-center justify-center px-5 py-12 sm:px-8">
      <div className="w-full max-w-sm animate-rise">
        <div className="mb-8 flex items-center gap-2.5">
          <ForgeMark />
          <span className="text-[15px] font-semibold tracking-[0.18em] text-ink">FORGE</span>
        </div>
        <h1 className="font-display text-[38px] leading-[1.1] text-ink">{title}</h1>
        {lead && <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">{lead}</p>}
        <div className="mt-8">{children}</div>
      </div>
    </main>
  );
}

export function Notice({ tone, children }: { tone: "error" | "success"; children: ReactNode }) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={`rounded-lg px-3.5 py-2.5 text-[14px] ${tone === "error" ? "bg-alert-soft text-alert" : "bg-positive-soft text-positive"}`}
    >
      {children}
    </p>
  );
}
