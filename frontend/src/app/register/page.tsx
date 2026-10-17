// D:\FYP\FORGE-1\frontend\src\app\register\page.tsx
import { Suspense } from "react";
import type { Metadata } from "next";
import { AuthForm } from "@/components/auth/AuthForm";
import { PageLoading } from "@/components/auth/RequireAuth";

export const metadata: Metadata = { title: "Create account — FORGE" };

export default function RegisterPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <AuthForm mode="register" />
    </Suspense>
  );
}
