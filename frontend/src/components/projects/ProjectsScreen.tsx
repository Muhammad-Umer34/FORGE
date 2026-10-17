// D:\FYP\FORGE-1\frontend\src\components\projects\ProjectsScreen.tsx
"use client";

// Your projects (D-174): up to three, each holding its own website requests. The backend enforces
// the limit; this screen only explains it and greys out "New project" when it is reached.

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/AuthProvider";
import { PageLoading } from "@/components/auth/RequireAuth";
import { StudioHeader } from "@/components/clarification/StudioHeader";
import { ApiError } from "@/services/client";
import { createProject, deleteProject, listProjects } from "@/services/projects";
import { MAX_PROJECTS, Project } from "@/types/auth";
import { DeleteProjectDialog } from "./DeleteProjectDialog";

const fieldClass =
  "mt-1.5 block w-full rounded-lg border border-line bg-paper px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint " +
  "focus:border-ember focus:outline-none focus:ring-2 focus:ring-ember/25";

const dateFormat = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" });

function NewProjectForm({ onCreate, onCancel }: { onCreate: (name: string, description: string) => Promise<void>; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onCreate(name.trim(), description);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The project could not be created. Please try again.");
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="animate-rise rounded-2xl border border-line bg-surface p-6 shadow-card">
      <h2 className="text-[17px] font-semibold text-ink">New project</h2>
      <label className="mt-4 block text-[14px] font-medium text-ink">
        Name
        <input
          className={fieldClass}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Sweet Crumbs Bakery"
          maxLength={60}
          autoFocus
          required
        />
      </label>
      <label className="mt-4 block text-[14px] font-medium text-ink">
        Short description <span className="font-normal text-ink-faint">(optional)</span>
        <input
          className={fieldClass}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What is this website for?"
          maxLength={500}
        />
      </label>
      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-alert-soft px-3.5 py-2.5 text-[14px] text-alert">
          {error}
        </p>
      )}
      <div className="mt-6 flex justify-end gap-2">
        <button type="button" onClick={onCancel} disabled={busy} className="rounded-lg px-4 py-2.5 text-[14px] font-medium text-ink-muted hover:bg-surface-sunk hover:text-ink disabled:opacity-40">
          Cancel
        </button>
        <button type="submit" disabled={!name.trim() || busy} className="rounded-lg bg-ink px-4 py-2.5 text-[14px] font-medium text-paper hover:opacity-90 disabled:opacity-40">
          {busy ? "Creating…" : "Create project"}
        </button>
      </div>
    </form>
  );
}

export function ProjectsScreen() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<Project | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setProjects(await listProjects());
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Your projects could not be loaded.");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load the list once, when the page opens
    load();
  }, [load]);

  const atLimit = (projects?.length ?? 0) >= MAX_PROJECTS;

  const create = async (name: string, description: string) => {
    const project = await createProject(name, description);
    setProjects((list) => [...(list ?? []), project]);
    setCreating(false);
  };

  const remove = async (project: Project) => {
    await deleteProject(project.id);
    setProjects((list) => (list ?? []).filter((p) => p.id !== project.id));
    setDeleting(null);
  };

  return (
    <>
      <StudioHeader />
      <main id="main" className="relative z-[1] mx-auto w-full max-w-3xl flex-1 px-5 pt-12 pb-16 sm:px-8 sm:pt-16">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[14px] text-ink-muted">Hello{user ? `, ${user.display_name}` : ""}</p>
            <h1 className="mt-1 font-display text-[40px] leading-[1.1] text-ink">Your projects</h1>
          </div>
          {projects && (
            <div className="flex items-center gap-3">
              <span className="text-[13px] text-ink-muted" aria-live="polite">
                {projects.length} of {MAX_PROJECTS} used
              </span>
              <button
                type="button"
                onClick={() => setCreating(true)}
                disabled={atLimit || creating}
                title={atLimit ? "Delete a project to create another" : undefined}
                className="rounded-lg bg-ink px-4 py-2.5 text-[14px] font-medium text-paper transition-opacity hover:opacity-90 disabled:opacity-40"
              >
                New project
              </button>
            </div>
          )}
        </div>

        {atLimit && !creating && (
          <p className="mt-4 text-[14px] text-ink-muted">You can have up to {MAX_PROJECTS} projects. Delete one to create another.</p>
        )}

        <div className="mt-8 space-y-4">
          {creating && <NewProjectForm onCreate={create} onCancel={() => setCreating(false)} />}

          {loadError && (
            <div role="alert" className="rounded-xl bg-alert-soft px-4 py-3 text-[14px] text-alert">
              {loadError}{" "}
              <button type="button" onClick={load} className="font-medium underline underline-offset-4">
                Try again
              </button>
            </div>
          )}

          {!projects && !loadError && <PageLoading label="Loading your projects" />}

          {projects?.length === 0 && !creating && (
            <div className="rounded-2xl border border-dashed border-line px-6 py-12 text-center">
              <p className="text-[16px] font-medium text-ink">No projects yet</p>
              <p className="mx-auto mt-2 max-w-sm text-[14px] leading-relaxed text-ink-muted">
                A project holds one website idea, like your bakery or your salon. Create one, then describe the website you need.
              </p>
              <button type="button" onClick={() => setCreating(true)} className="mt-5 rounded-lg bg-ink px-4 py-2.5 text-[14px] font-medium text-paper hover:opacity-90">
                Create your first project
              </button>
            </div>
          )}

          {projects && projects.length > 0 && (
            <ul className="grid gap-4 sm:grid-cols-2">
              {projects.map((project) => (
                <li key={project.id} className="group relative flex flex-col rounded-2xl border border-line bg-surface p-5 shadow-card transition-colors hover:border-ember/50">
                  <h2 className="pr-8 text-[17px] font-semibold text-ink">
                    <Link href={`/projects/${project.id}`} className="after:absolute after:inset-0 after:rounded-2xl focus:outline-none">
                      {project.name}
                    </Link>
                  </h2>
                  {project.description && <p className="mt-1.5 line-clamp-2 text-[14px] text-ink-muted">{project.description}</p>}
                  <p className="mt-auto pt-4 text-[12px] text-ink-faint">Created {dateFormat.format(new Date(project.created_at))}</p>
                  <button
                    type="button"
                    onClick={() => setDeleting(project)}
                    aria-label={`Delete ${project.name}`}
                    className="absolute right-3 top-3 z-10 rounded-md px-2 py-1 text-[12px] font-medium text-ink-faint hover:bg-alert-soft hover:text-alert focus:text-alert"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>

      {deleting && <DeleteProjectDialog project={deleting} onCancel={() => setDeleting(null)} onDelete={remove} />}
    </>
  );
}
