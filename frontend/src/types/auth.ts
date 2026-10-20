// D:\FYP\FORGE-1\frontend\src\types\auth.ts
// Sign-in and projects API types. They mirror backend/models/auth.py, projects.py and requests.py.

import { RequestStatus } from "./request";

export interface User {
  id: string;
  email: string;
  display_name: string;
  email_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
  notice?: string | null; // e.g. the verification email could not be sent today
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

/** One line in a project's list of website requests. */
export interface RequestSummary {
  id: string;
  prompt: string;
  status: "processing" | Exclude<RequestStatus, "reply">;
  created_at: string;
  updated_at: string;
}

/** Same number as MAX_PROJECTS_PER_USER in backend/services/projects.py (D-174). */
export const MAX_PROJECTS = 3;
