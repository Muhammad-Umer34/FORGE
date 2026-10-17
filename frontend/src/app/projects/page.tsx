// D:\FYP\FORGE-1\frontend\src\app\projects\page.tsx
import type { Metadata } from "next";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { ProjectsScreen } from "@/components/projects/ProjectsScreen";

export const metadata: Metadata = { title: "Your projects — FORGE" };

export default function ProjectsPage() {
  return (
    <RequireAuth>
      <ProjectsScreen />
    </RequireAuth>
  );
}
