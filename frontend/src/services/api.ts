// D:\FYP\FORGE-1\frontend\src\services\api.ts
import { ChatApiResponse, ResetApiResponse } from "@/types/chat";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

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
