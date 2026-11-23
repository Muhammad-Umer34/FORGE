// D:\FYP\FORGE-1\frontend\src\components\clarification\DataKeep.tsx
"use client";

// "What your site will keep" (D-244): every list the site stores, its fields and rules, in the owner's words (all
// text comes from code). Before approval the owner can add or remove a field, make one required, turn a rule on or
// off, change a rule's number, or undo. Every edit is applied by code on the server; nothing here calls a model.

import { useState } from "react";
import { DataEdit, DataTable } from "@/types/request";

interface DataKeepProps {
  tables: DataTable[];
  types: string[];
  editsLeft: number;
  canUndo: boolean;
  readOnly: boolean;
  busy: boolean;
  onEdit: (edit: DataEdit) => void;
}

const ROLE_WORDS: Record<DataTable["role"], string> = {
  submission: "Visitors send these",
  catalogue: "You manage these",
  setting: "Your settings",
};

const small = "text-[13px] font-medium text-ink-muted transition-colors duration-200 hover:text-ink disabled:opacity-50";

function AddField({ table, types, busy, onEdit, onClose }: {
  table: DataTable; types: string[]; busy: boolean; onEdit: (e: DataEdit) => void; onClose: () => void;
}) {
  const [label, setLabel] = useState("");
  const [type, setType] = useState(types[0] ?? "Short text");
  const [options, setOptions] = useState("");
  const [required, setRequired] = useState(false);
  const isChoice = type === "Choice from a list";
  const choices = options.split(",").map((o) => o.trim()).filter(Boolean);
  const ready = label.trim().length > 0 && (!isChoice || choices.length >= 2);
  const id = `add-${table.name}`;
  return (
    <form
      className="mt-3 grid gap-3 rounded-lg border border-line bg-surface p-4 sm:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!ready) return;
        onEdit({ op: "add_field", entity: table.name, label: label.trim(), type, required,
                 options: isChoice ? choices : [] });
        onClose();
      }}
    >
      <label className="text-[13px] text-ink-muted" htmlFor={`${id}-label`}>
        Field name
        <input id={`${id}-label`} autoFocus maxLength={60} value={label} onChange={(e) => setLabel(e.target.value)}
               placeholder="For example: Hair length"
               className="mt-1 block w-full rounded-md border border-line bg-paper px-3 py-2 text-[14px] text-ink focus:border-ember/60 focus:outline-none" />
      </label>
      <label className="text-[13px] text-ink-muted" htmlFor={`${id}-type`}>
        Kind of answer
        <select id={`${id}-type`} value={type} onChange={(e) => setType(e.target.value)}
                className="mt-1 block w-full rounded-md border border-line bg-paper px-3 py-2 text-[14px] text-ink focus:border-ember/60 focus:outline-none">
          {types.map((t) => <option key={t}>{t}</option>)}
        </select>
      </label>
      {isChoice && (
        <label className="text-[13px] text-ink-muted sm:col-span-2" htmlFor={`${id}-options`}>
          Answers to pick from, separated by commas
          <input id={`${id}-options`} value={options} onChange={(e) => setOptions(e.target.value)}
                 placeholder="Short, Medium, Long"
                 className="mt-1 block w-full rounded-md border border-line bg-paper px-3 py-2 text-[14px] text-ink focus:border-ember/60 focus:outline-none" />
        </label>
      )}
      <label className="flex items-center gap-2 text-[14px] text-ink">
        <input type="checkbox" checked={required} aria-label="Visitors must fill it in" onChange={(e) => setRequired(e.target.checked)} />
        Visitors must fill it in
      </label>
      <div className="flex items-center gap-4 sm:justify-end">
        <button type="submit" disabled={busy || !ready}
                className="rounded-lg bg-ink px-4 py-2 text-[13px] font-medium text-paper hover:bg-ember-strong disabled:cursor-not-allowed disabled:bg-surface-sunk disabled:text-ink-faint">
          Add field
        </button>
        <button type="button" onClick={onClose} className={small}>Cancel</button>
      </div>
    </form>
  );
}

function RuleNumber({ table, rule, busy, onEdit }: {
  table: DataTable; rule: DataTable["rules"][number]; busy: boolean; onEdit: (e: DataEdit) => void;
}) {
  const n = rule.number!;
  const [value, setValue] = useState(String(n.value));
  const parsed = Number(value);
  const valid = value.trim() !== "" && Number.isFinite(parsed) && parsed >= n.min && parsed <= n.max;
  const id = `num-${rule.rule_id}`;
  return (
    <span className="ml-1 inline-flex items-center gap-2">
      <label htmlFor={id} className="sr-only">Number for: {rule.label}</label>
      <input id={id} type="number" min={n.min} max={n.max} value={value} disabled={busy}
             onChange={(e) => setValue(e.target.value)}
             className="w-20 rounded-md border border-line bg-paper px-2 py-1 text-[13px] text-ink focus:border-ember/60 focus:outline-none" />
      <span className="text-[12px] text-ink-faint">{n.unit}</span>
      {valid && parsed !== n.value && (
        <button type="button" disabled={busy} className={small}
                onClick={() => onEdit({ op: "set_number", entity: table.name, rule_id: rule.rule_id, value: parsed })}>
          Save
        </button>
      )}
    </span>
  );
}

export function DataKeep({ tables, types, editsLeft, canUndo, readOnly, busy, onEdit }: DataKeepProps) {
  const [adding, setAdding] = useState<string | null>(null);
  const editable = !readOnly && editsLeft > 0;
  return (
    <div className="space-y-6">
      {!readOnly && (
        <p className="text-[13px] text-ink-muted">
          You can add or remove fields and change the rules before you approve.
          {canUndo && (
            <button type="button" disabled={busy} onClick={() => onEdit({ op: "undo" })} className={`ml-3 ${small} underline`}>
              Undo last change
            </button>
          )}
        </p>
      )}
      {tables.map((table) => (
        <div key={table.name}>
          <p className="text-[15px] font-medium text-ink">
            {table.label} <span className="text-[13px] font-normal text-ink-faint">· {ROLE_WORDS[table.role]}</span>
          </p>
          <ul className="mt-2 space-y-1.5">
            {table.fields.map((f) => (
              <li key={f.name} className="flex flex-wrap items-baseline gap-x-3 text-[14px] text-ink">
                <span>{f.label}</span>
                <span className="text-[12px] text-ink-faint">
                  {f.kind}{f.options.length > 0 && `: ${f.options.join(", ")}`}
                  {f.required ? " · required" : " · optional"}{f.personal && " · personal"}
                </span>
                {editable && f.can_toggle_required && (
                  <button type="button" disabled={busy} className={small}
                          onClick={() => onEdit({ op: "set_required", entity: table.name, field: f.name, required: !f.required })}>
                    {f.required ? "Make optional" : "Make required"}
                  </button>
                )}
                {editable && f.removable && (
                  <button type="button" disabled={busy} className={small}
                          onClick={() => onEdit({ op: "remove_field", entity: table.name, field: f.name })}>
                    Remove
                  </button>
                )}
                {!readOnly && f.why_fixed && (
                  <span className="text-[12px] text-ink-faint" title={`Stays because it is ${f.why_fixed}`}>
                    (stays: {f.why_fixed})
                  </span>
                )}
              </li>
            ))}
          </ul>
          {table.rules.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {table.rules.map((r) => (
                <li key={r.rule_id} className="flex flex-wrap items-center gap-x-2 text-[14px]">
                  {editable && r.can_toggle ? (
                    <label className="flex items-center gap-2 text-ink">
                      <input type="checkbox" checked={r.enabled} disabled={busy} aria-label={`Rule: ${r.label}`}
                             onChange={(e) => onEdit({ op: "toggle_rule", entity: table.name, rule_id: r.rule_id, enabled: e.target.checked })} />
                      <span className={r.enabled ? "" : "text-ink-faint line-through"}>{r.label}</span>
                    </label>
                  ) : (
                    <span className={r.enabled ? "text-ink" : "text-ink-faint line-through"}>
                      <span aria-hidden="true">{r.enabled ? "✓ " : "· "}</span>{r.label}
                      {r.locked && !readOnly && <span className="text-[12px] text-ink-faint"> (your answer)</span>}
                    </span>
                  )}
                  {editable && r.enabled && r.number && <RuleNumber table={table} rule={r} busy={busy} onEdit={onEdit} />}
                </li>
              ))}
            </ul>
          )}
          {editable && table.can_add_field && (adding === table.name ? (
            <AddField table={table} types={types} busy={busy} onEdit={onEdit} onClose={() => setAdding(null)} />
          ) : (
            <button type="button" disabled={busy} onClick={() => setAdding(table.name)} className={`mt-2 ${small}`}>
              + Add a field
            </button>
          ))}
        </div>
      ))}
      {!readOnly && editsLeft === 0 && (
        <p className="text-[13px] text-ink-faint">No more data changes can be made. Undo one, or approve the plan.</p>
      )}
    </div>
  );
}
