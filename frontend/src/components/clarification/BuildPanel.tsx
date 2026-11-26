"use client";

import { BuildEvent, FrontendInput } from "@/services/requests";

/** The frontend agent at work (D-240): its progress, what it received from the plan, and the live site. The
 *  preview is FORGE's dev server; it updates itself over its own WebSocket as the agent writes each page. */
export function BuildPanel({ events, running }: { events: BuildEvent[]; running: boolean }) {
  const input = events.find((e) => e.input)?.input;
  const url = [...events].reverse().find((e) => e.url)?.url;
  const lines = events.filter((e) => e.message);
  const last = lines[lines.length - 1];
  // The data and frontend agents run side by side (D-253), so their lines come interleaved: one list per agent.
  const groups = GROUPS.map((g) => ({ ...g, lines: lines.filter((e) => (e.agent ?? "frontend") === g.agent) }))
    .filter((g) => g.lines.length);

  return (
    <section aria-label="Building your site" className="mb-10 space-y-6">
      <div aria-live="polite" className="grid gap-5 sm:grid-cols-2">
        {groups.map((g) => (
          <div key={g.agent}>
            <h3 className="text-[12px] font-medium uppercase tracking-wide text-ink-faint">{g.title}</h3>
            <ol aria-label={`${g.title} progress`} className="mt-1.5 space-y-1 text-[14px] text-ink-muted">
              {g.lines.map((e, i) => (
                <li key={i} className="animate-rise">
                  {e.message}
                  {running && e === last && <span className="ml-1 animate-pulse">…</span>}
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>

      {input && <AgentInput input={input} />}

      {url && (
        <div className="relative left-1/2 w-[min(1280px,calc(100vw-2rem))] -translate-x-1/2 space-y-2">
          <div className="flex items-center justify-between gap-4 text-[14px]">
            <p className="font-medium text-ink">Live preview</p>
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-ember-strong underline-offset-2 hover:underline"
            >
              Open in a new tab
            </a>
          </div>
          <iframe
            src={url}
            title="Live preview of your site"
            className="h-[80vh] w-full rounded-xl border border-line bg-white shadow-sm"
          />
        </div>
      )}
    </section>
  );
}

const GROUPS = [
  { agent: "database", title: "Database" },
  { agent: "backend", title: "Backend" },
  { agent: "frontend", title: "Frontend" },
  { agent: "integration", title: "Integration" },
];

function AgentInput({ input }: { input: FrontendInput }) {
  const sections = input.pages.reduce((n, p) => n + p.sections.length, 0);
  return (
    <details className="rounded-xl border border-line bg-surface/60 px-4 py-3 text-[14px]">
      <summary className="cursor-pointer font-medium text-ink">
        What the frontend agent received: {input.pages.length} pages, {sections} sections, {input.texts} texts
      </summary>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1 font-medium text-ink">Pages and sections</p>
          <ul className="space-y-2 text-ink-muted">
            {input.pages.map((p) => (
              <li key={p.route}>
                <span className="text-ink">{p.title}</span> <code className="text-[12px]">{p.route}</code>
                <ul className="ml-4 list-disc">
                  {p.sections.map((s) => (
                    <li key={s.section}>
                      {s.component}
                      {s.variant ? ` (${s.variant})` : ""}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-3 text-ink-muted">
          <div>
            <p className="mb-1 font-medium text-ink">Design direction</p>
            <ul>
              {Object.entries(input.direction).map(([k, v]) => (
                <li key={k}>
                  {k.replace(/_/g, " ")}: <span className="text-ink">{String(v)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-1 font-medium text-ink">Theme</p>
            <p className="flex items-center gap-2">
              {input.theme.primary && (
                <span
                  aria-hidden
                  className="inline-block h-4 w-4 rounded-full border border-line"
                  style={{ background: input.theme.primary }}
                />
              )}
              {input.theme.fonts?.heading ?? "Inter"} / {input.theme.fonts?.body ?? "Inter"}, {input.theme.mode ?? "light"}
            </p>
          </div>
          <p>Site-wide: {input.site_wide.join(", ")}</p>
          <p>{input.content_fields} business details (sample content until the owner fills them)</p>
        </div>
      </div>
    </details>
  );
}
