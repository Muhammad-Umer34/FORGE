// D:\FYP\FORGE-1\frontend\src\services\requests.ts
// Website-request API (backend/routes/requests.py). Every request belongs to a project (D-179).

import { ConfirmationDecision, ImageColours, RequestEnvelope, UserAnswer } from "@/types/request";
import { apiFetch } from "./client";

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

/** Upload a logo or website screenshot; our backend returns its main colours (no model call, not stored). */
export function readImageColours(projectId: string, requestId: string, kind: "logo" | "screenshot", file: File): Promise<ImageColours> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch(`${one(projectId, requestId)}/image?kind=${kind}`, { method: "POST", body: form });
}
