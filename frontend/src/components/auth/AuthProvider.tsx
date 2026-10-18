// D:\FYP\FORGE-1\frontend\src\components\auth\AuthProvider.tsx
"use client";

// Who is signed in, for every page (D-181). On load the app asks the backend to renew the session
// from the HttpOnly refresh cookie; that is the only way to know, because page scripts can't read it.

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { onSignedOut } from "@/services/client";
import * as authApi from "@/services/auth";
import { User } from "@/types/auth";

type Status = "loading" | "signed_in" | "signed_out";

interface AuthValue {
  status: Status;
  user: User | null;
  signedOutByUser: boolean; // true after "Sign out"; false when the session ran out
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  reloadSession: () => Promise<void>; // after the email is verified: a new access token says so
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [signedOutByUser, setSignedOutByUser] = useState(false);

  const signedOut = useCallback(() => {
    setUser(null);
    setStatus("signed_out");
  }, []);

  const signedIn = (next: User) => {
    setUser(next);
    setSignedOutByUser(false);
    setStatus("signed_in");
  };

  const reloadSession = useCallback(async () => {
    const session = await authApi.refreshSession();
    if (session) setUser(session.user);
  }, []);

  useEffect(() => {
    let active = true;
    authApi
      .refreshSession()
      .then((session) => {
        if (!active) return;
        if (session) {
          setUser(session.user);
          setStatus("signed_in");
        } else {
          signedOut();
        }
      })
      .catch(() => active && signedOut()); // backend unreachable: show sign-in, which explains the error
    const unsubscribe = onSignedOut(signedOut);
    return () => {
      active = false;
      unsubscribe();
    };
  }, [signedOut]);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      user,
      signedOutByUser,
      login: async (email, password) => signedIn((await authApi.login(email, password)).user),
      register: async (email, password, displayName) =>
        signedIn((await authApi.register(email, password, displayName)).user),
      logout: async () => {
        try {
          await authApi.logout();
        } finally {
          setSignedOutByUser(true);
          signedOut();
        }
      },
      reloadSession,
    }),
    [status, user, signedOutByUser, signedOut, reloadSession],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
