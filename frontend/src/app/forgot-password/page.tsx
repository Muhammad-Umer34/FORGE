// D:\FYP\FORGE-1\frontend\src\app\forgot-password\page.tsx
import { Suspense } from "react";
import type { Metadata } from "next";
import { ForgotPasswordForm } from "@/components/auth/PasswordReset";
import { PageLoading } from "@/components/auth/RequireAuth";

export const metadata: Metadata = { title: "Forgot password — FORGE" };

export default function Page() {
  // The link's token is only known at request time, so the form streams in behind Suspense.
  return (
    <Suspense fallback={<PageLoading />}>
      <ForgotPasswordForm />
    </Suspense>
  );
}
