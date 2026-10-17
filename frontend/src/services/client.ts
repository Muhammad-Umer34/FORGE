// D:\FYP\FORGE-1\frontend\src\services\client.ts
// One place for every call to the FORGE backend (D-181).
// - Calls go to /api/* on this site; next.config.ts forwards them to FastAPI.
// - The access token lives only in this module's memory (never localStorage), so page scripts
//   injected by an attacker can't find it in storage. The refresh token is an HttpOnly cookie the
//   browser sends to /api/auth only.
// - If a call answers 401, the client refreshes once (shared by all callers and all tabs) and retries.

import { TokenResponse } from "@/types/auth";

/** An API failure with a message that is safe to show to the user. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
  }
}

const NETWORK_MESSAGE = "We couldn't reach FORGE. Check that the server is running, then try again.";

let accessToken: string | null = null;
let refreshing: Promise<TokenResponse | null> | null = null;
const signedOutListeners = new Set<() => void>();

export function setAccessToken(token: string | null) {
  accessToken = token;
}

/** Called when the session can't be renewed, so the app can show the sign-in page. */
export function onSignedOut(listener: () => void): () => void {
  signedOutListeners.add(listener);
  return () => signedOutListeners.delete(listener);
}

async function readError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => ({}));
  const detail = body?.detail;
  if (typeof detail === "string") return new ApiError(response.status, detail);
  if (detail && typeof detail.message === "string") return new ApiError(response.status, detail.message, detail.code);
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
    return new ApiError(response.status, detail[0].msg.replace(/^Value error, /, ""), "invalid");
  }
  return new ApiError(response.status, `FORGE returned an error (${response.status}). Please try again.`);
}

async function send(path: string, init: RequestInit, withToken: boolean): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (withToken && accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  try {
    return await fetch(path, { ...init, headers, cache: "no-store", credentials: "same-origin" });
  } catch {
    throw new ApiError(0, NETWORK_MESSAGE);
  }
}

async function refreshOnce(): Promise<TokenResponse | null> {
  const attempt = async (): Promise<TokenResponse | null> => {
    for (let tries = 0; tries < 3; tries++) {
      const response = await send("/api/auth/refresh", { method: "POST" }, false);
      if (response.ok) return response.json();
      // 409: another tab renewed the session a moment ago; the browser now has its new cookie.
      if (response.status === 409) {
        await new Promise((resolve) => setTimeout(resolve, 250 * (tries + 1)));
        continue;
      }
      if (response.status === 401) return null;
      throw await readError(response);
    }
    return null;
  };
  // Tabs take turns, so two tabs never spend the same refresh token at once.
  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  return locks ? locks.request("forge-refresh", attempt) : attempt();
}

/** Renew the session from the refresh cookie. Resolves to null when the user is signed out. */
export function refreshSession(): Promise<TokenResponse | null> {
  if (!refreshing) {
    refreshing = refreshOnce()
      .then((result) => {
        setAccessToken(result?.access_token ?? null);
        return result;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

/** A call to the backend. Signed-in calls retry once after renewing an expired access token. */
export async function apiFetch<T>(path: string, init: RequestInit = {}, { auth = true } = {}): Promise<T> {
  let response = await send(path, init, auth);
  if (auth && response.status === 401) {
    const renewed = await refreshSession();
    if (!renewed) {
      signedOutListeners.forEach((listener) => listener());
      throw new ApiError(401, "Please sign in again.", "signed_out");
    }
    response = await send(path, init, true);
  }
  if (!response.ok) throw await readError(response);
  return (response.status === 204 ? undefined : await response.json()) as T;
}
