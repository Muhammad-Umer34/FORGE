"use client"

// One form for everything a visitor sends (D-248): the Backend Agent writes its spec from the plan (lib/forms.json),
// so every field the site keeps is here, including the ones the owner added. Lists (services, stylists) and free
// times come from the site's own data routes; the server checks everything again and answers in plain words.

import React, { useEffect, useId, useRef, useState } from "react"
import { CheckCircle2, Loader2, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

export interface DataFormField {
  name: string
  label: string
  kind: string
  required: boolean
  personal?: boolean
  options?: string[]
  multiple?: boolean
  list?: { table: string; label: string }
  min?: number
  max?: number
  max_length?: number
  default?: string
}

export interface DataFormSpec {
  table: string
  label?: string
  fields: DataFormField[]
  consent?: boolean
  items?: { table: string; label?: string; fields: DataFormField[] }
  times?: { field: string; picks: string[] }
  texts?: Record<string, string>
}

export interface DataFormProps {
  spec: DataFormSpec
  className?: string
}

type Values = Record<string, string | boolean | string[]>
type Row = Record<string, unknown> & { id: string }

const INPUT_TYPES: Record<string, string> = {
  email: "email", phone: "tel", url: "url", image: "url", number: "number", money: "number", duration: "number",
  date: "date", time: "time", datetime: "datetime-local",
}

function useList(table: string | undefined): Row[] {
  const [rows, setRows] = useState<Row[]>([])
  useEffect(() => {
    if (!table) return
    let live = true
    fetch(`/api/data/${table}`)
      .then((r) => r.json())
      .then((body) => { if (live && Array.isArray(body?.rows)) setRows(body.rows as Row[]) })
      .catch(() => {})
    return () => { live = false }
  }, [table])
  return rows
}

function ListSelect({ field, id, value, invalid, describedBy, onChange }: {
  field: DataFormField; id: string; value: string; invalid: boolean; describedBy?: string; onChange: (v: string) => void
}) {
  const rows = useList(field.list?.table)
  const labelKey = field.list?.label ?? "name"
  return (
    <select id={id} value={value} required={field.required} aria-invalid={invalid} aria-describedby={describedBy}
            onChange={(e) => onChange(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive">
      <option value="">{rows.length ? "Choose…" : "Loading…"}</option>
      {rows.map((r) => <option key={r.id} value={r.id}>{String(r[labelKey] ?? r.id)}</option>)}
    </select>
  )
}

function FieldInput({ field, id, value, invalid, describedBy, onChange }: {
  field: DataFormField; id: string; value: Values[string] | undefined; invalid: boolean; describedBy?: string
  onChange: (v: Values[string]) => void
}) {
  const common = { id, required: field.required, "aria-invalid": invalid, "aria-describedby": describedBy }
  if (field.kind === "reference") {
    return <ListSelect field={field} id={id} value={String(value ?? "")} invalid={invalid} describedBy={describedBy}
                       onChange={onChange} />
  }
  if (field.kind === "boolean") {
    return <input {...common} type="checkbox" checked={value === true} onChange={(e) => onChange(e.target.checked)}
                  className="h-4 w-4 accent-primary" />
  }
  if (field.kind === "choice" && field.options) {
    if (field.multiple) {
      const chosen = Array.isArray(value) ? value : []
      return (
        <div role="group" aria-labelledby={`${id}-label`} className="flex flex-wrap gap-3">
          {field.options.map((o) => (
            <label key={o} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={chosen.includes(o)} className="h-4 w-4 accent-primary"
                     onChange={(e) => onChange(e.target.checked ? [...chosen, o] : chosen.filter((x) => x !== o))} />
              {o}
            </label>
          ))}
        </div>
      )
    }
    return (
      <select {...common} value={String(value ?? "")} onChange={(e) => onChange(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive">
        <option value="">Choose…</option>
        {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    )
  }
  if (field.kind === "long_text") {
    return <Textarea {...common} value={String(value ?? "")} maxLength={field.max_length} rows={4}
                     onChange={(e) => onChange(e.target.value)} />
  }
  return (
    <Input {...common} type={INPUT_TYPES[field.kind] ?? "text"} value={String(value ?? "")} maxLength={field.max_length}
           min={field.min} max={field.max} step={field.kind === "money" ? "0.01" : undefined}
           onChange={(e) => onChange(e.target.value)} />
  )
}

function FreeTimes({ table, field, picks, values, id, invalid, onPick }: {
  table: string; field: DataFormField; picks: string[]; values: Values; id: string; invalid: boolean
  onPick: (iso: string) => void
}) {
  const [day, setDay] = useState("")
  const [times, setTimes] = useState<string[] | null>(null)
  const chosen = String(values[field.name] ?? "")
  const ready = picks.every((p) => values[p])
  useEffect(() => {
    if (!day || !ready) return
    let live = true
    const query = new URLSearchParams({ date: day })
    picks.forEach((p) => query.set(p, String(values[p])))
    fetch(`/api/data/${table}/availability?${query.toString()}`)
      .then((r) => r.json())
      .then((body) => { if (live) setTimes(Array.isArray(body?.times) ? body.times : []) })
      .catch(() => { if (live) setTimes([]) })
    return () => { live = false }
  }, [day, ready, table, picks, values])
  return (
    <div className="space-y-3">
      <Input id={id} type="date" value={day} aria-invalid={invalid} min={new Date().toISOString().slice(0, 10)}
             onChange={(e) => { setDay(e.target.value); setTimes(null) }} />
      {!ready && <p className="text-xs text-muted-foreground">Choose the options above first to see free times.</p>}
      {day && ready && times === null && <p className="text-xs text-muted-foreground">Looking for free times…</p>}
      {times && times.length === 0 && <p className="text-sm text-muted-foreground">No free times that day. Please try another day.</p>}
      {times && times.length > 0 && (
        <div role="group" aria-label={`Free times on ${day}`} className="flex flex-wrap gap-2">
          {times.map((t) => {
            const iso = `${day}T${t}`
            return (
              <button key={t} type="button" aria-pressed={chosen === iso} onClick={() => onPick(iso)}
                      className={cn("rounded-md border px-3 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
                                    chosen === iso ? "border-primary bg-primary text-primary-foreground" : "border-border hover:bg-muted")}>
                {t}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function DataForm({ spec, className }: DataFormProps) {
  const formId = useId()
  const status = useRef<HTMLDivElement>(null)
  const start = Object.fromEntries(spec.fields.filter((f) => f.default !== undefined)
    .map((f) => [f.name, f.kind === "boolean" ? f.default === "true" : String(f.default)]))
  const [values, setValues] = useState<Values>(start)
  const [items, setItems] = useState<Values[]>(spec.items ? [{}] : [])
  const [consent, setConsent] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const texts = spec.texts ?? {}
  const itemList = useList(spec.items?.fields.find((f) => f.kind === "reference")?.list?.table)

  useEffect(() => { if (message) status.current?.focus() }, [message])

  const set = (name: string, value: Values[string]) => setValues((v) => ({ ...v, [name]: value }))

  function clean(source: Values, fields: DataFormField[]) {
    const out: Record<string, unknown> = {}
    for (const f of fields) {
      const v = source[f.name]
      if (v === undefined || v === "" || (Array.isArray(v) && v.length === 0)) continue
      out[f.name] = v
    }
    return out
  }

  async function send(e: React.FormEvent) {
    e.preventDefault()
    setErrors({})
    setMessage(null)
    const missing = spec.fields.filter((f) => f.required && f.kind !== "boolean" && !values[f.name])
    if (missing.length) {
      setErrors(Object.fromEntries(missing.map((f) => [f.name, `Please fill in '${f.label}'.`])))
      setMessage({ ok: false, text: `Please fill in '${missing[0].label}'.` })
      return
    }
    const body: Record<string, unknown> = clean(values, spec.fields)
    if (spec.items) body.items = items.map((i) => clean(i, spec.items!.fields)).filter((i) => Object.keys(i).length)
    if (spec.consent) body.consent = consent
    setBusy(true)
    try {
      const res = await fetch(`/api/data/${spec.table}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      })
      const answer = await res.json().catch(() => ({}))
      if (res.ok) {
        setMessage({ ok: true, text: answer.message || texts.successMessage || "Thank you, we've received it." })
        setValues(start)
        setItems(spec.items ? [{}] : [])
        setConsent(false)
      } else {
        if (answer.field) setErrors({ [answer.field]: answer.message })
        setMessage({ ok: false, text: answer.message || "Something went wrong. Please try again." })
      }
    } catch {
      setMessage({ ok: false, text: "We couldn't send that. Please check your connection and try again." })
    } finally {
      setBusy(false)
    }
  }

  const visible = spec.fields.filter((f) => !(spec.times && f.name === spec.times.field))
  const timeField = spec.times ? spec.fields.find((f) => f.name === spec.times!.field) : undefined

  return (
    <section className={cn("w-full py-16 sm:py-24 bg-background", className)}>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        {texts.badgeText && <p className="text-sm font-medium text-primary">{texts.badgeText}</p>}
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          {texts.title || spec.label || "Send us your details"}
        </h2>
        {texts.subtitle && <p className="mt-3 text-muted-foreground">{texts.subtitle}</p>}

        <form onSubmit={send} noValidate aria-describedby={`${formId}-status`}
              className="mt-8 grid gap-5 rounded-xl border border-border bg-card p-6 sm:grid-cols-2">
          {visible.map((f) => {
            const id = `${formId}-${f.name}`
            const err = errors[f.name]
            const wide = f.kind === "long_text" || f.kind === "boolean" || (f.kind === "choice" && f.multiple)
            return (
              <div key={f.name} className={cn("space-y-2", wide && "sm:col-span-2", f.kind === "boolean" && "flex items-center gap-3 space-y-0")}>
                <Label htmlFor={id} id={`${id}-label`} className={f.kind === "boolean" ? "order-last" : undefined}>
                  {f.label}{f.required && <span aria-hidden="true" className="text-destructive"> *</span>}
                </Label>
                <FieldInput field={f} id={id} value={values[f.name]} invalid={!!err}
                            describedBy={err ? `${id}-error` : undefined} onChange={(v) => set(f.name, v)} />
                {err && <p id={`${id}-error`} className="text-xs text-destructive">{err}</p>}
              </div>
            )
          })}

          {timeField && spec.times && (
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor={`${formId}-when`}>
                {timeField.label}{timeField.required && <span aria-hidden="true" className="text-destructive"> *</span>}
              </Label>
              <FreeTimes table={spec.table} field={timeField} picks={spec.times.picks} values={values}
                         id={`${formId}-when`} invalid={!!errors[timeField.name]} onPick={(iso) => set(timeField.name, iso)} />
              {errors[timeField.name] && <p className="text-xs text-destructive">{errors[timeField.name]}</p>}
            </div>
          )}

          {spec.items && (
            <fieldset className="space-y-3 sm:col-span-2">
              <legend className="text-sm font-medium text-foreground">{spec.items.label || "Items"}</legend>
              {items.map((item, n) => (
                <div key={n} className="flex flex-wrap items-end gap-3 rounded-md border border-border p-3">
                  {spec.items!.fields.map((f) => {
                    const id = `${formId}-item-${n}-${f.name}`
                    return (
                      <div key={f.name} className="min-w-[8rem] flex-1 space-y-1">
                        <Label htmlFor={id}>{f.label}</Label>
                        {f.kind === "reference" ? (
                          <select id={id} value={String(item[f.name] ?? "")} required={f.required}
                                  onChange={(e) => setItems((all) => all.map((x, i) => i === n ? { ...x, [f.name]: e.target.value } : x))}
                                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50">
                            <option value="">Choose…</option>
                            {itemList.map((r) => <option key={r.id} value={r.id}>{String(r[f.list?.label ?? "name"] ?? r.id)}</option>)}
                          </select>
                        ) : (
                          <FieldInput field={f} id={id} value={item[f.name]} invalid={false}
                                      onChange={(v) => setItems((all) => all.map((x, i) => i === n ? { ...x, [f.name]: v } : x))} />
                        )}
                      </div>
                    )
                  })}
                  {items.length > 1 && (
                    <Button type="button" variant="ghost" size="sm" aria-label={`Remove item ${n + 1}`}
                            onClick={() => setItems((all) => all.filter((_, i) => i !== n))}>
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  )}
                </div>
              ))}
              {items.length < 50 && (
                <Button type="button" variant="outline" size="sm" onClick={() => setItems((all) => [...all, {}])}>
                  <Plus className="mr-1 h-4 w-4" aria-hidden="true" /> Add item
                </Button>
              )}
            </fieldset>
          )}

          {spec.consent && (
            <div className="flex items-start gap-3 sm:col-span-2">
              <input id={`${formId}-consent`} type="checkbox" checked={consent} required
                     onChange={(e) => setConsent(e.target.checked)} className="mt-1 h-4 w-4 accent-primary" />
              <Label htmlFor={`${formId}-consent`} className="font-normal leading-snug text-muted-foreground">
                I agree that my details are kept to handle this request.
              </Label>
            </div>
          )}

          <div ref={status} tabIndex={-1} id={`${formId}-status`} role={message?.ok ? "status" : "alert"}
               className="sm:col-span-2 outline-none">
            {message && (
              <p className={cn("flex items-start gap-2 rounded-md px-3 py-2 text-sm",
                               message.ok ? "bg-primary/10 text-foreground" : "bg-destructive/10 text-destructive")}>
                {message.ok && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />}
                {message.text}
              </p>
            )}
          </div>

          <div className="sm:col-span-2">
            <Button type="submit" disabled={busy} className="w-full sm:w-auto">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {texts.submitButtonText || "Send"}
            </Button>
          </div>
        </form>
      </div>
    </section>
  )
}
