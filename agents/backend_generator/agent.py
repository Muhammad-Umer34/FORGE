# D:\FYP\FORGE-1\agents\backend_generator\agent.py
"""
The Backend Agent (D-247, D-248): code only, no model call. From the plan's data it writes, for each site,
- lib/forms.json: one form spec per form section (fields, links to lists, consent, order items, free times), read by
  the template's DataForm;
- lib/schemas.ts: a zod schema per form, the site's first check before anything reaches FORGE;
- api/contract.json: the routes the site uses, for the Integration Agent and the report;
and runs the backend gate: through FORGE's real data service, a valid submission is saved, one missing a required
field and one with an unknown field are refused, and public lists hold no personal data (all rolled back).
The route handlers themselves are the same for every site (site_template/app/api/data/).
"""
import json
from typing import Callable

from agents.file_store import active_store
from agents.planning.assemble import form_sections
from agents.state import AgentArtifacts, BuildPlan, DataEntity, DataField, RunConfig

FORM_TEXTS = ("badgeText", "title", "subtitle", "submitButtonText", "successMessage")


class BackendBuildError(RuntimeError):
    """The backend gate failed: a FORGE bug (all of this is code-made), never the user's fault."""


# ---------------------------------------------------------------- what visitors fill in
def worked_out(e: DataEntity) -> set[str]:
    return {"status"} | {r.params.get("end") for r in e.rules if r.kind == "end_from_duration" and r.enabled}


def label_field(e: DataEntity) -> str:
    """The field a dropdown shows for a row of this list (a stylist's name, an event's title)."""
    names = [f.name for f in e.fields]
    return next((n for n in ("name", "title") if n in names),
                next((f.name for f in e.fields if f.type == "text"), "id"))


def _field(f: DataField, by_name: dict[str, DataEntity]) -> dict:
    spec = {"name": f.name, "label": f.label or f.name.replace("_", " ").capitalize(), "kind": f.type,
            "required": f.required and f.default is None, "personal": f.personal}
    if f.options:
        spec["options"] = f.options
    if f.multiple:
        spec["multiple"] = True
    if f.type == "reference" and f.reference in by_name:
        spec["list"] = {"table": f.reference, "label": label_field(by_name[f.reference])}
    for key in ("min", "max", "max_length"):
        if getattr(f, key) is not None:
            spec[key] = getattr(f, key)
    if f.default is not None:
        spec["default"] = f.default
    return spec


def child_of(entities: list[DataEntity], parent: DataEntity) -> tuple[DataEntity, str] | None:
    """An order's items: a submission table without a status whose required link points at `parent`."""
    for e in entities:
        if e.role == "submission" and not any(f.name == "status" for f in e.fields):
            link = next((f.name for f in e.fields if f.type == "reference" and f.reference == parent.name
                         and f.required), None)
            if link:
                return e, link
    return None


def form_specs(plan: BuildPlan) -> dict[str, dict]:
    """Section id -> the form DataForm draws for it, for every form section on a recipe record type."""
    by_name = {e.name: e for e in plan.data_entities}
    routes = {r.route_id: r for r in plan.api_routes}
    texts = {t.slot_id: t.text for t in plan.texts}
    rules = {r.section_id: r for r in plan.form_rules}
    # A form section, or any section a recipe table's POST route serves: live, the planner put the slot picker (no
    # submit of its own) on the booking page, and the booking route listed it (journal #34).
    posted = {sid: r for r in plan.api_routes if r.method == "POST" for sid in r.used_by}
    out = {}
    for sid in dict.fromkeys([*form_sections(plan), *posted]):
        rule = rules.get(sid)
        route = routes.get(rule.route_id) if rule else posted.get(sid)
        e = by_name.get(route.entity or "") if route else None
        if not e or not e.pattern or e.role != "submission":
            continue
        hidden = worked_out(e)
        fields = [_field(f, by_name) for f in e.fields if f.name not in hidden and not (f.type == "reference" and f.multiple)]
        consent = rule.consent_required if rule else any(f.personal for f in e.fields)
        spec = {"table": e.name, "label": e.label, "fields": fields, "consent": consent,
                "texts": {k: texts[f"{sid}.{k}"] for k in FORM_TEXTS if texts.get(f"{sid}.{k}")}}
        child = child_of(plan.data_entities, e)
        if child:
            item, link = child
            spec["items"] = {"table": item.name, "label": item.label,
                             "fields": [_field(f, by_name) for f in item.fields if f.name != link]}
        kinds = {r.kind: r.params for r in e.rules if r.enabled}
        timing = kinds.get("no_overlap") or kinds.get("within_hours")
        start = next((f for f in e.fields if timing and f.name == timing.get("start")), None)
        if start and start.type == "datetime":
            spec["times"] = {"field": start.name,
                             "picks": [p for p in (timing.get("resource"), (kinds.get("end_from_duration") or {}).get("via"))
                                       if p]}
        out[sid] = spec
    return out


# ---------------------------------------------------------------- lib/schemas.ts (zod)
def _ts(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _zod(f: dict) -> str:
    label, k = f["label"], f["kind"]
    fill = _ts(f"Please fill in '{label}'.")
    check = _ts(f"Please check '{label}'.")
    if k == "choice":
        base = f"z.enum({_ts(f['options'])}, {{ error: {check} }})"
        base = f"z.array({base})" if f.get("multiple") else base
    elif k in ("number", "money", "duration"):
        base = f"z.coerce.number({{ error: {check} }})" + (".int()" if k == "duration" else "")
        base += "".join(f".{op}({f[key]:g}, {{ error: {check} }})" for op, key in (("min", "min"), ("max", "max"))
                        if f.get(key) is not None)
    elif k == "boolean":
        base = f"z.boolean({{ error: {check} }})"
    elif k == "reference":
        base = f"z.uuid({{ error: {_ts('Please choose a valid ' + label.lower() + '.')} }})"
    elif k == "email":
        email_msg = "Please check '" + label + "': an email address like name@example.com"
        base = f"z.email({{ error: {_ts(email_msg)} }})"
    else:                                                # error: also the message when the field is missing (live)
        base = f"z.string({{ error: {fill if f['required'] else check} }}).trim()"
        if f.get("max_length"):
            long_msg = "Please keep '" + label + "' under " + str(f["max_length"]) + " characters."
            base += f".max({f['max_length']}, {{ error: {_ts(long_msg)} }})"
        if f["required"]:
            base += f".min(1, {{ error: {fill} }})"
    return base if f["required"] else f"{base}.optional()"


def schemas_ts(specs: dict[str, dict]) -> str:
    """One strict zod object per form table: only the fields the form shows, with the plan's labels in messages."""
    tables: dict[str, str] = {}
    for spec in specs.values():
        body = [f"  {f['name']}: {_zod(f)}," for f in spec["fields"]]
        if spec.get("items"):
            item = ", ".join(f"{f['name']}: {_zod(f)}" for f in spec["items"]["fields"])
            body.append(f"  items: z.array(z.object({{ {item} }}).strict()).min(1, {{ error: "
                        f"{_ts('Please add at least one item.')} }}).max(50),")
        if spec.get("consent"):
            body.append(f"  consent: z.literal(true, {{ error: {_ts('Please tick the box to agree.')} }}),")
        tables[spec["table"]] = "z.object({\n" + "\n".join(body) + "\n}).strict()"
    lines = ["// Written by FORGE's Backend Agent from the plan (D-247). Do not edit: it is rewritten on every build.",
             'import { z } from "zod"', "", "export const schemas: Record<string, z.ZodTypeAny> = {"]
    lines += [f"  {name}: {schema.replace(chr(10), chr(10) + '  ')}," for name, schema in tables.items()]
    return "\n".join(lines + ["}", ""])


def contract_json(plan: BuildPlan, specs: dict[str, dict]) -> str:
    return json.dumps({"routes": [r.model_dump(include={"route_id", "method", "path", "entity", "request_fields",
                                                        "used_by"}) for r in plan.api_routes],
                       "forms": {sid: s["table"] for sid, s in specs.items()}}, indent=2)


# ---------------------------------------------------------------- the build step
def run(plan: BuildPlan, request_id: str, project_id: str, config: RunConfig, progress: Callable[[dict], None],
        storage=None) -> AgentArtifacts:
    """Write the site's backend files; with real storage (`storage`, from the Database Agent), run the backend gate."""
    def say(message: str) -> None:
        progress({"agent": "backend", "message": message})

    specs = form_specs(plan)
    if not specs:
        say("Backend: no forms send anything; nothing to connect")
        return AgentArtifacts(agent="backend", status="done")
    say(f"Backend: {len(specs)} form{'s' if len(specs) != 1 else ''} on {len(plan.api_routes)} route"
        f"{'s' if len(plan.api_routes) != 1 else ''}")
    files = {"lib/forms.json": json.dumps(specs, indent=2, ensure_ascii=False), "lib/schemas.ts": schemas_ts(specs),
             "api/contract.json": contract_json(plan, specs)}
    if storage is not None:
        from agents.backend_generator.gate import run_gate
        passed, total, failures = run_gate(storage, plan, specs)
        say(f"Backend: {passed}/{total} checks passed")
        if failures:
            say(f"Backend: {'; '.join(failures[:3])}. This is a FORGE bug, not yours.")
            raise BackendBuildError("; ".join(failures))
    refs = active_store().put(request_id, files, "code", kind="backend")
    return AgentArtifacts(agent="backend", status="done", files=refs)
