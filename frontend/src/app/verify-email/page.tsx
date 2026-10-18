// D:\FYP\FORGE-1\frontend\src\app\verify-email\page.tsx
import { Suspense } from "react";
import type { Metadata } from "next";
import { VerifyEmailScreen } from "@/components/auth/EmailVerification";
import { PageLoading } from "@/components/auth/RequireAuth";

export const metadata: Metadata = { title: "Verify email — FORGE" };

export default function Page() {
  // The link's token is only known at request time, so the form streams in behind Suspense.
  return (
    <Suspense fallback={<PageLoading />}>
      <VerifyEmailScreen />
    </Suspense>
  );
}
