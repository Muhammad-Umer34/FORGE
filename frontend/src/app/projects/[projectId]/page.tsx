// D:\FYP\FORGE-1\frontend\src\app\projects\[projectId]\page.tsx
import { Suspense } from "react";
import type { Metadata } from "next";
import { PageLoading, RequireAuth } from "@/components/auth/RequireAuth";
import { ProjectStudio } from "@/components/projects/ProjectStudio";

export const metadata: Metadata = { title: "Project — FORGE" };

export default function ProjectPage({ params }: PageProps<"/projects/[projectId]">) {
  // The project id is only known at request time, so the studio streams in behind Suspense.
  return (
    <RequireAuth>
      <Suspense fallback={<PageLoading label="Opening your project" />}>
        <ProjectStudio params={params} />
      </Suspense>
    </RequireAuth>
  );
}
