// D:\FYP\FORGE-1\frontend\src\services\siteData.ts
// The owner's view of what their site keeps (backend/routes/owner_data.py, D-250).

import { apiFetch } from "./client";

export interface DataColumn {
  name: string;
  label: string | null;
  type: string;
  options: string[] | null;
  required: boolean;
  personal: boolean;
  reference: string | null;
  min: number | null;
  max: number | null;
  max_length: number | null;
  visitor: boolean;
}

export interface DataTableSummary {
  name: string;
  label: string;
  role: "submission" | "catalogue" | "setting";
  rows: number;
  new_today: number;
  moves: Record<string, string[]>;
  columns: DataColumn[];
}

export type DataRow = Record<string, unknown> & { id: string; created_at: string; is_sample: boolean };

export interface DataPage {
  rows: DataRow[];
  more: boolean;
  names: Record<string, Record<string, string>>;
}

const base = (projectId: string) => `/api/projects/${encodeURIComponent(projectId)}/data`;

export function listTables(projectId: string): Promise<{ tables: DataTableSummary[] }> {
  return apiFetch(base(projectId));
}

export function listRows(projectId: string, table: string, page = 0): Promise<DataPage> {
  return apiFetch(`${base(projectId)}/${encodeURIComponent(table)}?page=${page}`);
}

export function updateRow(projectId: string, table: string, id: string, values: Record<string, unknown>): Promise<void> {
  return apiFetch(`${base(projectId)}/${encodeURIComponent(table)}/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(values),
  });
}

export function addRow(projectId: string, table: string, values: Record<string, unknown>): Promise<{ id: string }> {
  return apiFetch(`${base(projectId)}/${encodeURIComponent(table)}`, { method: "POST", body: JSON.stringify(values) });
}

export function deleteRow(projectId: string, table: string, id: string): Promise<void> {
  return apiFetch(`${base(projectId)}/${encodeURIComponent(table)}/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function clearSamples(projectId: string): Promise<{ removed: number; kept: number }> {
  return apiFetch(`${base(projectId)}/clear-samples`, { method: "POST" });
}
