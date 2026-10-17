// D:\FYP\FORGE-1\frontend\src\app\login\page.tsx
import { Suspense } from "react";
import type { Metadata } from "next";
import { AuthForm } from "@/components/auth/AuthForm";
import { PageLoading } from "@/components/auth/RequireAuth";

export const metadata: Metadata = { title: "Sign in — FORGE" };

export default function LoginPage() {
  // AuthForm reads ?next=, which is only known at request time, so it streams in behind Suspense.
  return (
    <Suspense fallback={<PageLoading />}>
      <AuthForm mode="login" />
    </Suspense>
  );
}
