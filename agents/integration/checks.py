# D:\FYP\FORGE-1\agents\integration\checks.py
"""
Job 2 of the Integration Agent (D-252): the joins between the parts, checked by code on the site's files. Each agent's
own gate checks its part; these check that the parts fit:

I1  every DataForm on a page has its spec in lib/forms.json
I2  every form posts to a POST route of api/contract.json, on a submission table
I3  every route's table is in db/schema.json with the right role (POST: submission; GET: catalogue or setting;
    /availability: a booking table with opening hours or a no-overlap rule)
I4  a form sends only visitor columns of its table, every required one, never a worked-out one
I5  every dropdown's list is a table visitors may read (catalogue or setting)
I6  order items: the items table links to the order table
I7  a form that collects personal data has the consent box; one that does not, has none
I8  lib/schemas.ts has one zod schema per form, with exactly the form's fields
I9  model-written parts call no API and read no environment
I10 every page of the plan has its file, and every link goes to a real page
I11 every dashboard view's table exists
I12 .env.example names what lib/forge.ts reads

Every side is made by code, so a failure is a FORGE bug, except I9: a model part that breaks it is replaced by its
plain section (the agent does that; here it is reported).
"""
import json
import re
from dataclasses import dataclass

from agents.build_worker import TEMPLATE
from agents.state import BuildPlan

FORBIDDEN_IN_MODEL_PARTS = re.compile(r"\bfetch\s*\(|['\"`]/api/|process\.env|@/lib/forge|XMLHttpRequest|axios")
_DATAFORM = "<DataForm {..."
_HREF = re.compile(r'"href":\s*"(/[^"]*)"|\bhref="(/[^"]*)"')
_SCHEMA_TABLE = re.compile(r"^  (\w+): z\.object\(\{$")
_SCHEMA_FIELD = re.compile(r"^    (\w+): ")


@dataclass
class Check:
    id: str
    ok: bool
    message: str


def page_path(route: str) -> str:
    return "app/page.tsx" if not route.strip("/") else f"app/{route.strip('/')}/page.tsx"


def page_forms(files: dict[str, str]) -> list[tuple[str, dict]]:
    """(page file, spec) for every DataForm the compiler placed; the spec is JSON in the page."""
    out, decoder = [], json.JSONDecoder()
    for path, text in files.items():
        if not (path.startswith("app/") and path.endswith(".tsx")):
            continue
        at = text.find(_DATAFORM)
        while at >= 0:
            props, _ = decoder.raw_decode(text, at + len(_DATAFORM))
            out.append((path, props["spec"]))
            at = text.find(_DATAFORM, at + 1)
    return out


def schema_fields(text: str) -> dict[str, list[str]]:
    """Table -> field names, read from the generated lib/schemas.ts."""
    out, table = {}, None
    for line in text.splitlines():
        if m := _SCHEMA_TABLE.match(line):
            table = out.setdefault(m.group(1), [])
        elif table is not None and (m := _SCHEMA_FIELD.match(line)):
            table.append(m.group(1))
        elif line.startswith("  })"):
            table = None
    return out


def _json(files: dict[str, str], path: str) -> dict:
    try:
        return json.loads(files.get(path) or "{}")
    except ValueError:
        return {}


def run_checks(files: dict[str, str], plan: BuildPlan, model_paths: set[str] = frozenset()) -> list[Check]:
    out: list[Check] = []

    def check(cid: str, ok: bool, message: str) -> None:
        out.append(Check(cid, bool(ok), message))

    forms = _json(files, "lib/forms.json")
    contract = _json(files, "api/contract.json")
    tables = {t["name"]: t for t in _json(files, "db/schema.json").get("tables", [])}
    routes = {r["route_id"]: r for r in contract.get("routes", [])}
    placed = page_forms(files)

    # I1
    specs = {json.dumps(s, sort_keys=True) for s in forms.values()}
    for page, spec in placed:
        check("I1", json.dumps(spec, sort_keys=True) in specs,
              f"{page}: its {spec.get('table')} form has no spec in lib/forms.json")
    for spec in forms.values():
        table, t = spec["table"], tables.get(spec["table"])
        name = f"the {spec.get('label') or table} form"
        # I2
        check("I2", f"POST /api/data/{table}" in routes, f"{name} posts to POST /api/data/{table}, which the site does not have")
        check("I2", t and t["role"] == "submission", f"{name} posts to '{table}', which is not a table visitors send")
        if not t:
            continue
        cols = {c["name"]: c for c in t["columns"]}
        visitor = {n for n, c in cols.items() if c["visitor"] and not (c["type"] == "reference" and c["multiple"])}
        sent = [f["name"] for f in spec["fields"]]
        # I4
        for f in sent:
            check("I4", f in visitor, f"{name} sends '{f}', which '{table}' does not take from visitors")
        for n in visitor:
            if cols[n]["required"] and cols[n]["default"] is None:
                check("I4", n in sent, f"{name} leaves out '{n}', which '{table}' needs")
        # I5
        for f in spec["fields"]:
            if lst := f.get("list"):
                lt = tables.get(lst["table"])
                check("I5", lt and lt["role"] in ("catalogue", "setting"),
                      f"{name}: the '{f['label']}' choice reads '{lst['table']}', which visitors may not read")
        # I6
        if items := spec.get("items"):
            it = tables.get(items["table"])
            link = it and any(c.get("reference") == table and c["required"] for c in it["columns"])
            check("I6", link, f"{name}: its items ('{items['table']}') do not link to '{table}'")
        # I7
        personal = any(f.get("personal") for f in spec["fields"])
        check("I7", spec.get("consent") == personal,
              f"{name} {'collects personal data but has no consent box' if personal else 'asks for consent but collects no personal data'}")
        # availability (I3)
        if spec.get("times"):
            kinds = {r["kind"] for r in t.get("rules", [])}
            check("I3", kinds & {"within_hours", "no_overlap"} and spec["times"]["field"] in visitor,
                  f"{name} shows free times, but '{table}' has no opening hours or no-overlap rule to work them out")
    # I3
    for rid, r in routes.items():
        t = tables.get(r.get("entity") or "")
        role = t and t["role"]
        if r["method"] == "POST":
            ok = role == "submission"
        elif r["path"].endswith("/availability"):
            ok = role == "submission" and {x["kind"] for x in t.get("rules", [])} & {"within_hours", "no_overlap"}
        else:
            ok = role in ("catalogue", "setting")
        check("I3", ok, f"{rid} uses '{r.get('entity')}', which "
                        + ("is not a table" if not t else f"is a {role} table, the wrong kind for this route"))
    # I8
    zod = schema_fields(files.get("lib/schemas.ts", "")) if forms else {}
    for spec in forms.values():
        want = ([f["name"] for f in spec["fields"]] + (["items"] if spec.get("items") else [])
                + (["consent"] if spec.get("consent") else []))
        got = zod.get(spec["table"])
        check("I8", got is not None and sorted(got) == sorted(want),
              f"lib/schemas.ts: the {spec['table']} schema has {sorted(got or [])}, the form sends {sorted(want)}")
    # I9
    for path in sorted(model_paths):
        if hit := FORBIDDEN_IN_MODEL_PARTS.search(files.get(path, "")):
            check("I9", False, f"{path} (written by AI) uses '{hit.group(0)}'; only FORGE's own forms may reach the API")
    # I10
    pages = {p.route.rstrip("/") or "/" for p in plan.pages}
    for p in plan.pages:
        check("I10", page_path(p.route) in files, f"the page {p.route} has no file")
    links = {(path, (m.group(1) or m.group(2)).split("#")[0].split("?")[0].rstrip("/") or "/")
             for path, text in files.items() if path.startswith(("app/", "content/", "components/"))
             for m in _HREF.finditer(text)}
    for path, href in sorted(links):
        if not href.startswith("/api/"):
            check("I10", href in pages, f"{path} links to {href}, which is not a page")
    # I11
    for v in plan.dashboard_views:
        check("I11", v.entity in tables or not tables, f"the dashboard shows '{v.entity}', which is not a table")
    # I12
    if forms:
        forge = (TEMPLATE / "lib" / "forge.ts").read_text(encoding="utf-8")
        for var in re.findall(r"process\.env\.(\w+)", forge):
            check("I12", f"{var}=" in files.get(".env.example", ""), f".env.example does not name {var}")
    return out


def failures(checks: list[Check]) -> list[Check]:
    return [c for c in checks if not c.ok]
