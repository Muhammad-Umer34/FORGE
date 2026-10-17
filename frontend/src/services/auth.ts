// D:\FYP\FORGE-1\frontend\src\services\auth.ts
// Sign-in API (backend/routes/auth.py). The refresh cookie is set and cleared by the backend.

import { TokenResponse } from "@/types/auth";
import { apiFetch, setAccessToken } from "./client";

async function signIn(path: string, body: object): Promise<TokenResponse> {
  const result = await apiFetch<TokenResponse>(path, { method: "POST", body: JSON.stringify(body) }, { auth: false });
  setAccessToken(result.access_token);
  return result;
}

export function register(email: string, password: string, displayName: string): Promise<TokenResponse> {
  return signIn("/api/auth/register", { email, password, display_name: displayName });
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return signIn("/api/auth/login", { email, password });
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<void>("/api/auth/logout", { method: "POST" }, { auth: false });
  } finally {
    setAccessToken(null);
  }
}

export { refreshSession } from "./client";
