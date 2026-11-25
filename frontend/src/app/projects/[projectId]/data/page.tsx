// D:\FYP\FORGE-1\frontend\src\app\projects\[projectId]\data\page.tsx
import { Suspense } from "react";
import type { Metadata } from "next";
import { PageLoading, RequireAuth } from "@/components/auth/RequireAuth";
import { SiteData } from "@/components/projects/SiteData";

export const metadata: Metadata = { title: "Site data — FORGE" };

export default function SiteDataPage({ params }: { params: Promise<{ projectId: string }> }) {
  return (
    <RequireAuth>
      <Suspense fallback={<PageLoading label="Opening your site's data" />}>
        <SiteData params={params} />
      </Suspense>
    </RequireAuth>
  );
}
