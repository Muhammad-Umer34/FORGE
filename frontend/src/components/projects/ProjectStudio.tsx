// D:\FYP\FORGE-1\frontend\src\components\projects\ProjectStudio.tsx
"use client";

// One project's page: finds the project among the user's own (the backend answers 404 for anyone
// else's), then opens the studio for it.

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { PageLoading } from "@/components/auth/RequireAuth";
import ForgeStudio from "@/components/clarification/ForgeStudio";
import { StudioHeader } from "@/components/clarification/StudioHeader";
import { ApiError } from "@/services/client";
import { listProjects } from "@/services/projects";
import { Project } from "@/types/auth";

export function ProjectStudio({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const [project, setProject] = useState<Project | null | undefined>(undefined); // undefined = loading, null = not found
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listProjects()
      .then((projects) => active && setProject(projects.find((p) => p.id === projectId) ?? null))
      .catch((err) => active && setError(err instanceof ApiError ? err.message : "This project could not be opened."));
    return () => {
      active = false;
    };
  }, [projectId]);

  if (project) return <ForgeStudio projectId={project.id} projectName={project.name} />;

  return (
    <>
      <StudioHeader />
      <main id="main" className="mx-auto w-full max-w-3xl flex-1 px-5 pt-16 pb-16 sm:px-8">
        {project === undefined && !error ? (
          <PageLoading label="Opening your project" />
        ) : (
          <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-card">
            <h1 className="text-[18px] font-semibold text-ink">{error ? "Something went wrong" : "Project not found"}</h1>
            <p className="mt-2 text-[14px] text-ink-muted">{error ?? "It may have been deleted, or it belongs to another account."}</p>
            <Link href="/projects" className="mt-5 inline-block rounded-lg bg-ink px-4 py-2.5 text-[14px] font-medium text-paper hover:opacity-90">
              Back to your projects
            </Link>
          </div>
        )}
      </main>
    </>
  );
}
