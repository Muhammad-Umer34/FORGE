// D:\FYP\FORGE-1\frontend\src\services\requests.ts
// Website-request API (backend/routes/requests.py). Every request belongs to a project (D-179).

import { ConfirmationDecision, ImageColours, PlanDecision, RequestEnvelope, UserAnswer } from "@/types/request";
import { apiEvents, apiFetch } from "./client";

const base = (projectId: string) => `/api/projects/${encodeURIComponent(projectId)}/requests`;
const one = (projectId: string, requestId: string) => `${base(projectId)}/${encodeURIComponent(requestId)}`;

export function createRequest(projectId: string, prompt: string): Promise<RequestEnvelope> {
  return apiFetch(base(projectId), { method: "POST", body: JSON.stringify({ prompt }) });
}

export function getRequest(projectId: string, requestId: string): Promise<RequestEnvelope> {
  return apiFetch(one(projectId, requestId));
}

export function answerQuestion(projectId: string, requestId: string, answer: UserAnswer): Promise<RequestEnvelope> {
  return apiFetch(`${one(projectId, requestId)}/answer`, { method: "POST", body: JSON.stringify(answer) });
}

export function confirmBrief(projectId: string, requestId: string, decision: ConfirmationDecision): Promise<RequestEnvelope> {
  return apiFetch(`${one(projectId, requestId)}/confirmation`, { method: "POST", body: JSON.stringify(decision) });
}

/** Approve the plan, ask for one change, or cancel it. */
export function decidePlan(projectId: string, requestId: string, decision: PlanDecision): Promise<RequestEnvelope> {
  return apiFetch(`${one(projectId, requestId)}/plan`, { method: "POST", body: JSON.stringify(decision) });
}

/** Continue a paused request from its last saved step. */
export function resumeRequest(projectId: string, requestId: string): Promise<RequestEnvelope> {
  return apiFetch(`${one(projectId, requestId)}/resume`, { method: "POST" });
}

/** End a paused request for good. */
export function cancelRequest(projectId: string, requestId: string): Promise<RequestEnvelope> {
  return apiFetch(`${one(projectId, requestId)}/cancel`, { method: "POST" });
}

/** Upload a logo or website screenshot; our backend returns its main colours (no model call, not stored). */
export function readImageColours(projectId: string, requestId: string, kind: "logo" | "screenshot", file: File): Promise<ImageColours> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch(`${one(projectId, requestId)}/image?kind=${kind}`, { method: "POST", body: form });
}

/** Follow a running step's progress lines (the build, D-233) until it ends. */
/** One progress event of a running build (D-233, D-240). `input`: what the frontend agent received; `url`: the live
 * preview; `file`: a page just written. */
export type BuildEvent = {
  message?: string;
  url?: string;
  file?: string;
  input?: FrontendInput;
};

export type FrontendInput = {
  business_type?: string | null;
  pages: { title: string; route: string; sections: { section: string; component: string; variant?: string | null }[] }[];
  site_wide: string[];
  direction: Record<string, string>;
  theme: { fonts?: { heading?: string; body?: string } | null; primary?: string | null; mode?: string };
  texts: number;
  content_fields: number;
};

/** Start the live preview of a built site again from its saved files (after a reload or a server restart). */
export function startPreview(projectId: string, requestId: string): Promise<{ url: string }> {
  return apiFetch(`${one(projectId, requestId)}/preview`, { method: "POST" });
}

export function followRun(projectId: string, requestId: string, onEvent: (event: BuildEvent) => void): Promise<void> {
  return apiEvents(`${one(projectId, requestId)}/events`, (data) => onEvent(data as BuildEvent));
}
