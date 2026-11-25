// D:\FYP\FORGE-1\frontend\src\components\projects\SiteData.tsx
"use client";

// "Your site's data" (D-250): what visitors sent and the owner's own lists, for one project. Statuses offer only the
// moves the site allows; the owner adds, edits and removes rows of their own lists. Every check happens on the
// server; messages come back in plain words.

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { StudioHeader } from "@/components/clarification/StudioHeader";
import { PageLoading } from "@/components/auth/RequireAuth";
import { ApiError } from "@/services/client";
import { listProjects } from "@/services/projects";
import {
  addRow, clearSamples, DataColumn, DataPage, DataTableSummary, deleteRow, listRows, listTables, updateRow,
} from "@/services/siteData";

const GROUPS: { role: DataTableSummary["role"]; title: string }[] = [
  { role: "submission", title: "Visitors send these" },
  { role: "catalogue", title: "You manage these" },
  { role: "setting", title: "Your settings" },
];

const INPUT: Record<string, string> = {
  email: "email", phone: "tel", url: "url", image: "url", number: "number", money: "number", duration: "number",
  date: "date", time: "time", datetime: "datetime-local",
};

const field = "w-full rounded-md border border-line bg-paper px-3 py-2 text-[14px] text-ink focus:border-ember/60 focus:outline-none";
const quiet = "text-[13px] font-medium text-ink-muted transition-colors duration-200 hover:text-ink disabled:opacity-40";

function label(c: DataColumn) {
  return c.label || c.name.replace(/_/g, " ").replace(/^./, (x) => x.toUpperCase());
}

function shown(value: unknown, c: DataColumn, names: DataPage["names"]): string {
  if (value === null || value === undefined || value === "") return "—";
  if (c.reference) return names[c.name]?.[String(value)] ?? "(removed)";
  if (c.type === "boolean") return value ? "Yes" : "No";
  if (c.type === "datetime") return new Date(String(value)).toLocaleString();
  if (c.type === "duration") return `${value} min`;
  return String(value);
}

function RowEditor({ table, row, names, onSave, onCancel, busy }: {
  table: DataTableSummary; row: Record<string, unknown> | null; names: DataPage["names"]
  onSave: (values: Record<string, unknown>) => void; onCancel: () => void; busy: boolean
}) {
  const cols = table.columns.filter((c) => c.visitor);
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(cols.map((c) => [c.name, row?.[c.name] ?? (c.type === "boolean" ? false : "")])));
  return (
    <form
      className="grid gap-4 rounded-xl border border-line bg-surface p-5 sm:grid-cols-2"
      onSubmit={(e) => { e.preventDefault(); onSave(values); }}
    >
      {cols.map((c) => {
        const id = `edit-${table.name}-${c.name}`;
        const v = values[c.name];
        const set = (x: unknown) => setValues((all) => ({ ...all, [c.name]: x }));
        return (
          <label key={c.name} htmlFor={id} className={`text-[13px] text-ink-muted ${c.type === "long_text" ? "sm:col-span-2" : ""}`}>
            {label(c)}{c.required && <span aria-hidden="true" className="text-alert"> *</span>}
            {c.reference ? (
              <select id={id} className={`mt-1 ${field}`} value={String(v ?? "")} onChange={(e) => set(e.target.value)}>
                <option value="">Choose…</option>
                {Object.entries(names[c.name] ?? {}).map(([k, n]) => <option key={k} value={k}>{n}</option>)}
              </select>
            ) : c.options?.length ? (
              <select id={id} className={`mt-1 ${field}`} value={String(v ?? "")} onChange={(e) => set(e.target.value)}>
                <option value="">Choose…</option>
                {c.options!.map((o) => <option key={o}>{o}</option>)}
              </select>
            ) : c.type === "boolean" ? (
              <input id={id} type="checkbox" className="mt-2 block h-4 w-4 accent-ember" checked={v === true}
                     onChange={(e) => set(e.target.checked)} />
            ) : c.type === "long_text" ? (
              <textarea id={id} className={`mt-1 ${field}`} rows={3} maxLength={c.max_length ?? undefined}
                        value={String(v ?? "")} onChange={(e) => set(e.target.value)} />
            ) : (
              <input id={id} type={INPUT[c.type] ?? "text"} className={`mt-1 ${field}`} maxLength={c.max_length ?? undefined}
                     min={c.min ?? undefined} max={c.max ?? undefined} value={String(v ?? "").slice(0, c.type === "datetime" ? 16 : undefined)}
                     onChange={(e) => set(e.target.value)} />
            )}
          </label>
        );
      })}
      <div className="flex items-center gap-4 sm:col-span-2">
        <button type="submit" disabled={busy}
                className="rounded-lg bg-ink px-4 py-2 text-[13px] font-medium text-paper hover:bg-ember-strong disabled:opacity-50">
          {row ? "Save" : "Add"}
        </button>
        <button type="button" onClick={onCancel} className={quiet}>Cancel</button>
      </div>
    </form>
  );
}

export function SiteData({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const [projectName, setProjectName] = useState<string | undefined>();
  const [tables, setTables] = useState<DataTableSummary[] | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [page, setPage] = useState<DataPage | null>(null);
  const [editing, setEditing] = useState<Record<string, unknown> | "new" | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [missing, setMissing] = useState<string | null>(null);

  const table = tables?.find((t) => t.name === active) ?? null;

  const loadTables = useCallback(() => listTables(projectId)
    .then(({ tables }) => {
      setTables(tables);
      setActive((a) => a ?? tables.find((t) => t.role === "submission")?.name ?? tables[0]?.name ?? null);
    })
    .catch((e) => setMissing(e instanceof ApiError ? e.message : "Your site's data could not be opened.")), [projectId]);

  useEffect(() => {
    listProjects().then((ps) => setProjectName(ps.find((p) => p.id === projectId)?.name)).catch(() => {});
    loadTables();
  }, [projectId, loadTables]);

  useEffect(() => {
    if (!active) return;
    listRows(projectId, active).then(setPage).catch((e) => setMessage({ ok: false, text: e.message }));
  }, [projectId, active]);

  async function act<T>(work: () => Promise<T>, done: string | ((result: T) => string)) {
    setBusy(true);
    setMessage(null);
    try {
      const result = await work();
      setMessage({ ok: true, text: typeof done === "string" ? done : done(result) });
      setEditing(null);
      await loadTables();
      if (active) setPage(await listRows(projectId, active));
    } catch (e) {
      setMessage({ ok: false, text: e instanceof ApiError ? e.message : "That did not work. Please try again." });
    } finally {
      setBusy(false);
    }
  }

  const ownList = table && table.role !== "submission";
  const columns = table?.columns.filter((c) => c.name !== "status" || table.role !== "submission") ?? [];

  return (
    <>
      <StudioHeader projectName={projectName} />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-5 pt-10 pb-16 sm:px-8">
        <Link href={`/projects/${projectId}`} className={quiet}>← Back to the studio</Link>
        <h1 className="mt-4 font-display text-[2.2rem] leading-tight text-ink">Your site&apos;s data</h1>
        <p className="mt-2 max-w-[62ch] text-[15px] text-ink-muted">
          What visitors send through your site, and the lists your site shows. Sample rows were added so the preview
          works; remove them when your own are in.
        </p>

        {missing ? (
          <p className="mt-8 rounded-lg border border-line bg-surface px-5 py-4 text-[15px] text-ink">{missing}</p>
        ) : !tables ? (
          <PageLoading label="Opening your site's data" />
        ) : (
          <div className="mt-8 grid gap-8 lg:grid-cols-[16rem_1fr]">
            <nav aria-label="Your site's lists" className="space-y-6">
              {GROUPS.map((g) => {
                const own = tables.filter((t) => t.role === g.role);
                if (!own.length) return null;
                return (
                  <div key={g.role}>
                    <p className="text-[12px] font-medium uppercase tracking-wide text-ink-faint">{g.title}</p>
                    <ul className="mt-2 space-y-1">
                      {own.map((t) => (
                        <li key={t.name}>
                          <button type="button" aria-current={t.name === active ? "page" : undefined}
                                  onClick={() => { if (t.name !== active) setPage(null); setActive(t.name); setEditing(null); setMessage(null); }}
                                  className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-[14px] ${t.name === active ? "bg-ember-soft text-ink" : "text-ink-muted hover:bg-surface"}`}>
                            <span>{t.label}</span>
                            <span className="text-[12px] text-ink-faint">
                              {t.rows}{t.new_today > 0 && <span className="ml-1.5 rounded bg-ember px-1.5 text-paper">{t.new_today} new</span>}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
              <button type="button" disabled={busy} className={quiet}
                      onClick={() => act(() => clearSamples(projectId), ({ removed, kept }) => kept
                        ? `Removed ${removed} sample rows. ${kept} stay because your own rows still use them; change those first.`
                        : `Removed ${removed} sample rows.`)}>
                Remove sample rows
              </button>
            </nav>

            <section aria-labelledby="list-title" className="min-w-0">
              {table && (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 id="list-title" className="text-[18px] font-semibold text-ink">{table.label}</h2>
                    {ownList && editing === null && (
                      <button type="button" onClick={() => setEditing("new")}
                              className="rounded-lg border border-line px-3 py-1.5 text-[13px] font-medium text-ink hover:bg-surface">
                        Add
                      </button>
                    )}
                  </div>
                  {message && (
                    <p role={message.ok ? "status" : "alert"}
                       className={`mt-3 rounded-lg px-4 py-2.5 text-[14px] ${message.ok ? "bg-positive/10 text-ink" : "bg-alert-soft text-alert"}`}>
                      {message.text}
                    </p>
                  )}
                  {editing !== null && page && (
                    <div className="mt-4">
                      <RowEditor table={table} row={editing === "new" ? null : editing} names={page.names} busy={busy}
                                 onCancel={() => setEditing(null)}
                                 onSave={(values) => act<unknown>(
                                   () => editing === "new" ? addRow(projectId, table.name, values)
                                     : updateRow(projectId, table.name, String((editing as Record<string, unknown>).id), values),
                                   editing === "new" ? "Added." : "Saved.")} />
                    </div>
                  )}
                  {!page ? (
                    <p className="mt-6 text-[14px] text-ink-muted">Loading…</p>
                  ) : page.rows.length === 0 ? (
                    <p className="mt-6 text-[14px] text-ink-muted">
                      {table.role === "submission" ? "Nothing yet. It appears here when visitors send it." : "This list is empty. Add the first row."}
                    </p>
                  ) : (
                    <div className="mt-4 overflow-x-auto rounded-xl border border-line">
                      <table className="w-full min-w-[40rem] text-left text-[14px]">
                        <thead className="bg-surface text-[12px] text-ink-muted">
                          <tr>
                            {table.role === "submission" && table.columns.some((c) => c.name === "status") && <th scope="col" className="px-3 py-2 font-medium">Status</th>}
                            {columns.map((c) => <th key={c.name} scope="col" className="px-3 py-2 font-medium">{label(c)}</th>)}
                            <th scope="col" className="px-3 py-2 font-medium">{ownList ? "Added" : "Received"}</th>
                            {ownList && <th scope="col" className="px-3 py-2"><span className="sr-only">Actions</span></th>}
                          </tr>
                        </thead>
                        <tbody>
                          {page.rows.map((row) => {
                            const status = String(row.status ?? "");
                            const next = table.moves[status] ?? [];
                            return (
                              <tr key={row.id} className="border-t border-line align-top">
                                {table.role === "submission" && table.columns.some((c) => c.name === "status") && (
                                  <td className="px-3 py-2">
                                    <label className="sr-only" htmlFor={`status-${row.id}`}>Status</label>
                                    <select id={`status-${row.id}`} value={status} disabled={busy || next.length === 0}
                                            onChange={(e) => act(() => updateRow(projectId, table.name, row.id, { status: e.target.value }), `Moved to ${e.target.value}.`)}
                                            className="rounded-md border border-line bg-paper px-2 py-1 text-[13px]">
                                      <option value={status}>{status}</option>
                                      {next.map((s) => <option key={s} value={s}>{s}</option>)}
                                    </select>
                                  </td>
                                )}
                                {columns.map((c) => (
                                  <td key={c.name} className="max-w-[16rem] truncate px-3 py-2 text-ink" title={String(row[c.name] ?? "")}>
                                    {shown(row[c.name], c, page.names)}
                                  </td>
                                ))}
                                <td className="whitespace-nowrap px-3 py-2 text-ink-muted">
                                  {new Date(row.created_at).toLocaleDateString()}
                                  {row.is_sample && <span className="ml-2 rounded bg-surface-sunk px-1.5 text-[11px] text-ink-faint">Sample</span>}
                                </td>
                                {ownList && (
                                  <td className="whitespace-nowrap px-3 py-2 text-right">
                                    <button type="button" className={quiet} disabled={busy} onClick={() => setEditing(row)}>Edit</button>
                                    <button type="button" className={`ml-3 ${quiet}`} disabled={busy}
                                            onClick={() => act(() => deleteRow(projectId, table.name, row.id), "Removed.")}>
                                      Remove
                                    </button>
                                  </td>
                                )}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </section>
          </div>
        )}
      </main>
    </>
  );
}
