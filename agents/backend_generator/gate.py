# D:\FYP\FORGE-1\agents\backend_generator\gate.py
"""
The backend gate (D-247): before the site goes live, FORGE's real data service is tried on the site's own storage,
inside one transaction that is always rolled back:
- for every form: a valid submission (built from a sample row, moved a week on) is saved; the same without one
  required field, and with an unknown field, are refused with plain messages;
- for every public list: no personal field comes back.
A failure is a FORGE bug: every part of this is code-made.
"""
from datetime import date, datetime, time, timedelta

import psycopg

from agents.database_generator.seed import seed_rows
from agents.state import BuildPlan


def _json(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def sample_payload(spec: dict, rows: dict[str, list[dict]], plan: BuildPlan) -> dict:
    """A submission a visitor could send: a sample row's visitor fields, its times moved a week on so it does not
    clash with the sample bookings, and a fresh email so a 'once per person' rule does not object."""
    base = dict((rows.get(spec["table"]) or [{}])[-1])
    out = {}
    for f in spec["fields"]:
        value = base.get(f["name"])
        if isinstance(value, (datetime, date)):
            value = value + timedelta(days=7)
        if f["kind"] == "email":
            value = "gate.check@example.com"
        if value is not None:
            out[f["name"]] = _json(value)
    if spec.get("items"):
        item_rows = rows.get(spec["items"]["table"]) or []
        out["items"] = [{f["name"]: _json(r[f["name"]]) for f in spec["items"]["fields"] if f["name"] in r}
                        for r in item_rows[:1]]
    return out


def run_gate(storage, plan: BuildPlan, specs: dict[str, dict]) -> tuple[int, int, list[str]]:
    """(checks passed, checks run, what failed)."""
    from backend.services import site_data
    rows = seed_rows(plan.data_entities, storage.contract.get("time_zone") or "Asia/Karachi")
    checks: list[tuple[str, bool]] = []
    with site_data.pool().connection() as conn:
        with conn.transaction(force_rollback=True):
            for spec in {s["table"]: s for s in specs.values()}.values():
                payload = sample_payload(spec, rows, plan)
                table = spec["table"]
                checks.append((f"{table}: a valid submission is saved", _saved(site_data, storage, table, payload, conn)))
                required = next((f["name"] for f in spec["fields"] if f["required"] and f["name"] in payload), None)
                if required:
                    missing = {k: v for k, v in payload.items() if k != required}
                    checks.append((f"{table}: a missing '{required}' is refused",
                                   _refused(site_data, storage, table, missing, conn, required)))
                checks.append((f"{table}: an unknown field is refused",
                               _refused(site_data, storage, table, {**payload, "gate_unknown": "x"}, conn,
                                        "gate_unknown")))
            for e in plan.data_entities:
                if e.role in ("catalogue", "setting"):
                    personal = {f.name for f in e.fields if f.personal}
                    listed = site_data.list_public(storage, e.name, conn)
                    checks.append((f"{e.name}: the public list holds no personal data",
                                   not any(personal & set(r) for r in listed)))
    failures = [name for name, ok in checks if not ok]
    return len(checks) - len(failures), len(checks), failures


def _saved(site_data, storage, table, payload, conn) -> bool:
    try:
        with conn.transaction(force_rollback=True):
            site_data.submit(storage, table, payload, conn)
        return True
    except (site_data.SiteDataError, psycopg.Error):
        return False


def _refused(site_data, storage, table, payload, conn, field) -> bool:
    try:
        with conn.transaction(force_rollback=True):
            site_data.submit(storage, table, payload, conn)
    except site_data.SiteDataError as error:
        return error.field == field and error.status == 422
    return False
