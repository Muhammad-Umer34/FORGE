# D:\FYP\FORGE-1\agents\integration\live.py
"""
Job 3 of the Integration Agent (D-254): prove the joined site works, through the site's OWN routes on the running
preview, so the whole path is tried: Next.js route, zod, lib/forge.ts, FORGE's API with the site key, the site's
role, the database. For each form:
1. its lists answer (GET /api/data/<list>), and a booking form's free times (GET .../availability);
2. a test submission is saved (201);
3. a broken one is refused: a repeat on a no-overlap table (409, the database's rule), else a missing required
   field (422, the site's zod check);
4. the saved rows are marked as samples and deleted (order items first), as the schema's owner, even when a
   step fails. shortcut: a process crash before clean-up leaves a row named "FORGE test"; mark rows right after
   saving if that is ever seen.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx
import psycopg

from agents.database_generator.compile import ident
from agents.database_generator.provision import plain_url

TIMEOUT_S = 20                                   # Supabase connections took ~7 s (KI-42)
DAYS_TO_TRY = 14


@dataclass
class LiveResult:
    steps: list[tuple[str, bool, str]] = field(default_factory=list)      # (what, ok, detail)
    saved: int = 0

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.steps)

    def add(self, what: str, ok: bool, detail: str = "") -> bool:
        self.steps.append((what, ok, detail))
        return ok


def _say(reply: httpx.Response) -> str:
    try:
        return f"{reply.status_code} {reply.json().get('message') or ''}".strip()
    except ValueError:
        return str(reply.status_code)


def check_live(base_url: str, forms: dict[str, dict], tables: dict[str, dict], schema: str, db_url: str,
               payload_for, tz: str = "Asia/Karachi") -> LiveResult:
    """`forms`: section id -> form spec; `tables`: db/schema.json tables by name; `payload_for(spec)`: a valid
    submission (the backend gate's sample payload)."""
    result, saved = LiveResult(), []                       # saved: (table, id, items table, its link column)
    with httpx.Client(base_url=base_url, timeout=TIMEOUT_S) as client:
        def call(method: str, path: str, **kw) -> httpx.Response:
            try:
                return client.request(method, path, **kw)
            except httpx.HTTPError:                        # the dev server compiles a route on its first call
                return client.request(method, path, **kw)
        try:
            for spec in {s["table"]: s for s in forms.values()}.values():
                _one_form(call, spec, tables, payload_for, tz, result, saved)
        finally:
            _clean_up(db_url, schema, saved, result)
    return result


def _one_form(call, spec, tables, payload_for, tz, result: LiveResult, saved: list) -> None:
    table, name = spec["table"], spec.get("label") or spec["table"]
    payload = payload_for(spec)
    if spec.get("consent"):                                # a visitor ticks it; the site's zod check needs it
        payload["consent"] = True
    for f in spec["fields"]:                               # real rows: the owner may have removed the samples
        if lst := f.get("list"):
            reply = call("GET", f"/api/data/{lst['table']}")
            rows = reply.json().get("rows", []) if reply.status_code == 200 else []
            if not result.add(f"{name}: the '{f['label']}' list answers", reply.status_code == 200, _say(reply)):
                return
            if rows:
                payload[f["name"]] = rows[0]["id"]
            elif f["required"]:
                result.add(f"{name}: the '{f['label']}' list has rows to choose from", False, "the list is empty")
                return
        elif f["name"] in ("client_name", "customer_name", "name", "full_name"):
            payload[f["name"]] = "FORGE test"
    if times := spec.get("times"):
        picks = {p: payload[p] for p in times["picks"] if payload.get(p)}
        day, free = date.today() + timedelta(days=1), []
        for _ in range(DAYS_TO_TRY):
            reply = call("GET", f"/api/data/{table}/availability", params={"date": day.isoformat(), **picks})
            if reply.status_code != 200:
                result.add(f"{name}: free times answer", False, _say(reply))
                return
            free = reply.json().get("times") or []
            if free:
                break
            day += timedelta(days=1)
        if not result.add(f"{name}: free times answer", bool(free), f"none in the next {DAYS_TO_TRY} days" if not free else
                          f"{len(free)} on {day.isoformat()}"):
            return
        payload[times["field"]] = f"{day.isoformat()}T{free[0]}"
    reply = call("POST", f"/api/data/{table}", json=payload)
    if not result.add(f"{name}: a submission through the site is saved", reply.status_code == 201, _say(reply)):
        return
    items = spec.get("items")
    link = next((c["name"] for c in tables.get(items["table"], {}).get("columns", []) if c.get("reference") == table),
                None) if items else None
    saved.append((table, reply.json()["id"], items["table"] if items else None, link))
    result.saved += 1
    rules = {r["kind"] for r in tables.get(table, {}).get("rules", [])}
    if "no_overlap" in rules:
        again = call("POST", f"/api/data/{table}", json=payload)
        result.add(f"{name}: the same time again is refused by the database", again.status_code == 409, _say(again))
        if again.status_code == 201:                       # wrongly saved: remove it too
            saved.append((table, again.json()["id"], None, None))
        return
    required = next((f["name"] for f in spec["fields"] if f["required"] and f["name"] in payload), None)
    if required:
        broken = {k: v for k, v in payload.items() if k != required}
        reply = call("POST", f"/api/data/{table}", json=broken)
        result.add(f"{name}: a missing '{required}' is refused by the site's check", reply.status_code == 422, _say(reply))


def _clean_up(db_url: str, schema: str, saved: list, result: LiveResult) -> None:
    """Mark, then delete, every row the check saved; order items first. As the schema's owner: the site's role may
    never delete what visitors sent."""
    if not saved:
        return
    try:
        with psycopg.connect(plain_url(db_url)) as conn, conn.transaction():
            for table, row_id, items, link in saved:
                t = f"{ident(schema)}.{ident(table)}"
                conn.execute(f"UPDATE {t} SET is_sample = true WHERE id = %s", (row_id,))
                if items and link:
                    conn.execute(f"DELETE FROM {ident(schema)}.{ident(items)} WHERE {ident(link)} = %s", (row_id,))
                conn.execute(f"DELETE FROM {t} WHERE id = %s", (row_id,))
        result.add("test rows removed", True, f"{len(saved)} removed")
    except psycopg.Error as error:
        result.add("test rows removed", False, f"{type(error).__name__}: {error}"[:200])

