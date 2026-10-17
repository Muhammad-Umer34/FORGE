// D:\FYP\FORGE-1\frontend\src\services\projects.ts
// Projects API (backend/routes/projects.py): at most 3 per user, deleted for good.

import { Project, RequestSummary } from "@/types/auth";
import { apiFetch } from "./client";

export function listProjects(): Promise<Project[]> {
  return apiFetch<Project[]>("/api/projects");
}

export function createProject(name: string, description?: string): Promise<Project> {
  return apiFetch<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ name, description: description?.trim() || null }),
  });
}

export function deleteProject(projectId: string): Promise<void> {
  return apiFetch<void>(`/api/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" });
}

export function listRequests(projectId: string): Promise<RequestSummary[]> {
  return apiFetch<RequestSummary[]>(`/api/projects/${encodeURIComponent(projectId)}/requests`);
}
