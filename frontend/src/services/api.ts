// D:\FYP\FORGE-1\frontend\src\services\api.ts
import { ChatApiResponse, ResetApiResponse } from "@/types/chat";
import {
  ConfirmationDecision,
  RequestEnvelope,
  UserAnswer,
} from "@/types/request";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// ---------------------------------------------------------------- website-request API

/** An API failure with a message that is safe to show to the user. */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const NETWORK_MESSAGE =
  "We couldn't reach FORGE. Check that the server is running, then try again.";

async function requestJson(path: string, init?: RequestInit): Promise<RequestEnvelope> {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, NETWORK_MESSAGE);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : null;
    throw new ApiError(response.status, detail ?? `FORGE returned an error (${response.status}). Please try again.`);
  }
  return response.json();
}

export function createRequest(prompt: string): Promise<RequestEnvelope> {
  return requestJson("/api/requests", { method: "POST", body: JSON.stringify({ prompt }) });
}

export function getRequest(requestId: string): Promise<RequestEnvelope> {
  return requestJson(`/api/requests/${encodeURIComponent(requestId)}`);
}

export function answerQuestion(requestId: string, answer: UserAnswer): Promise<RequestEnvelope> {
  return requestJson(`/api/requests/${encodeURIComponent(requestId)}/answer`, {
    method: "POST",
    body: JSON.stringify(answer),
  });
}

export function confirmBrief(requestId: string, decision: ConfirmationDecision): Promise<RequestEnvelope> {
  return requestJson(`/api/requests/${encodeURIComponent(requestId)}/confirmation`, {
    method: "POST",
    body: JSON.stringify(decision),
  });
}

// ---------------------------------------------------------------- old chat API (removed in the D-137 cleanup)

export async function sendChatMessage(
  message: string,
  sessionId?: string
): Promise<ChatApiResponse> {
  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: sessionId || undefined,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Server responded with status ${response.status}`
    );
  }

  return response.json();
}

export async function resetChatSession(
  sessionId: string
): Promise<ResetApiResponse> {
  const response = await fetch(`${BACKEND_URL}/api/chat/reset`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to reset session (status: ${response.status})`);
  }

  return response.json();
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: "GET",
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}
