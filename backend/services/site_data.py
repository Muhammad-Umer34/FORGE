# D:\FYP\FORGE-1\backend\services\site_data.py
"""
The site data service (D-247): what every generated site's server calls, through a few fixed routes. Each site's
contract (its db/schema.json, kept in site_storage) says which tables and fields exist; this module checks every
value against it, runs the query as the site's own database role, and turns the database's refusals into plain
messages. Values always go in as query parameters; names come only from the contract and are quoted.
Synchronous on purpose (psycopg pool); the routes call it in a worker thread.
"""
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Iterator
from zoneinfo import ZoneInfo

import psycopg
from psycopg_pool import ConnectionPool

from agents.database_generator.compile import FORMAT_CHECKS, ident

MAX_TEXT = 10_000
LIST_LIMIT = 200
HIDDEN_FLAGS = ("visible", "available", "open")   # a catalogue row with one of these set to false is not listed


class SiteDataError(Exception):
    """A request the site may show to its visitor: HTTP status, a plain message and, if known, the field."""

    def __init__(self, status: int, message: str, field: str | None = None):
        super().__init__(message)
        self.status, self.message, self.field = status, message, field


@dataclass
class Storage:
    """One site's storage, as kept in site_storage."""
    project_id: str
    schema: str
    role: str
    contract: dict

    def table(self, name: str) -> dict | None:
        return next((t for t in self.contract.get("tables", []) if t["name"] == name), None)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.contract.get("time_zone") or "Asia/Karachi")


_pool: ConnectionPool | None = None


def pool(url: str | None = None) -> ConnectionPool:
    """One small pool for every site's data (2 connections, so FORGE stays under Supabase's limit of 15)."""
    global _pool
    if _pool is None:
        from agents.database_generator.provision import plain_url
        from backend.core.config import settings
        _pool = ConnectionPool(plain_url(url or settings.SITE_DB_URL or settings.SUPABASE_DB_URL), min_size=0,
                               max_size=2, open=True, kwargs={"prepare_threshold": None},
                               check=ConnectionPool.check_connection)
    return _pool


def use_pool(p: ConnectionPool | None) -> None:
    """For tests: point the service at another database."""
    global _pool
    _pool = p


# ---------------------------------------------------------------- checking values
def _label(col: dict) -> str:
    return col.get("label") or col["name"].replace("_", " ").capitalize()


def check_value(col: dict, raw: Any, tz: ZoneInfo) -> Any:
    """One value -> the Python value PostgreSQL gets, or SiteDataError naming the field."""
    t, label = col["type"], _label(col)

    def bad(why: str = "") -> SiteDataError:
        return SiteDataError(422, f"Please check '{label}'{': ' + why if why else '.'}", col["name"])

    if isinstance(raw, str):
        raw = raw.strip()
    if t in ("text", "long_text", "email", "phone", "url", "image"):
        if not isinstance(raw, str):
            raise bad()
        limit = col.get("max_length") or MAX_TEXT
        if len(raw) > limit:
            raise bad(f"at most {limit} characters")
        if t in FORMAT_CHECKS and not re.match(FORMAT_CHECKS[t], raw, re.I):
            raise bad({"email": "an email address like name@example.com", "phone": "a phone number",
                       "url": "a web link starting with https://", "image": "a web link"}.get(t, ""))
        return raw
    if t in ("number", "money", "duration"):
        try:
            value = Decimal(str(raw))
        except Exception:
            raise bad("a number") from None
        if not value.is_finite() or (t == "duration" and value != value.to_integral_value()):
            raise bad("a number")
        if col.get("min") is not None and value < Decimal(str(col["min"])):
            raise bad(f"at least {col['min']:g}")
        if col.get("max") is not None and value > Decimal(str(col["max"])):
            raise bad(f"at most {col['max']:g}")
        return int(value) if t == "duration" else value
    if t == "boolean":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.lower() in ("true", "false", "on", "yes", "no"):
            return raw.lower() in ("true", "on", "yes")
        raise bad()
    if t == "choice":
        options = col.get("options") or []
        if col.get("multiple"):
            if not isinstance(raw, list) or any(v not in options for v in raw):
                raise bad(f"choose from {', '.join(options)}")
            return raw
        if raw not in options:
            raise bad(f"choose one of {', '.join(options)}")
        return raw
    if t == "reference":
        try:
            return uuid.UUID(str(raw))
        except ValueError:
            raise SiteDataError(422, f"Please choose a valid {label.lower()}.", col["name"]) from None
    try:
        if t == "date":
            return date.fromisoformat(str(raw))
        if t == "time":
            return time.fromisoformat(str(raw))
        if t == "datetime":
            value = datetime.fromisoformat(str(raw))
            return value if value.tzinfo else value.replace(tzinfo=tz)      # a plain time is the site's local time
    except ValueError:
        raise bad({"date": "a date", "time": "a time", "datetime": "a date and time"}[t]) from None
    raise bad()


def check_submission(table: dict, payload: Any, tz: ZoneInfo, skip: frozenset[str] = frozenset()) -> dict[str, Any]:
    """A visitor's payload -> the columns to insert. Only visitor fields; unknown fields refused; required ones
    present. Status, ids and worked-out fields are never taken from a visitor. `skip`: a child row's link to its
    parent, which code sets."""
    if not isinstance(payload, dict):
        raise SiteDataError(422, "The form could not be read. Please try again.")
    cols = {c["name"]: c for c in table["columns"] if c.get("visitor", True) and c["name"] != "status"
            and c["name"] not in skip}
    unknown = [k for k in payload if k not in cols and k not in ("status", "id", "created_at", "is_sample", "items", "consent")
               and not _worked_out(table, k)]
    if unknown:
        raise SiteDataError(422, "The form sent something this site does not keep.", unknown[0])
    out = {}
    for name, col in cols.items():
        raw = payload.get(name)
        if raw is None or raw == "" or raw == []:
            if col["required"] and col.get("default") is None:
                raise SiteDataError(422, f"Please fill in '{_label(col)}'.", name)
            continue
        out[name] = check_value(col, raw, tz)
    return out


def _worked_out(table: dict, name: str) -> bool:
    col = next((c for c in table["columns"] if c["name"] == name), None)
    return bool(col and not col.get("visitor", True))


# ---------------------------------------------------------------- plain messages for the database's refusals
def _hours(h: float) -> str:
    return f"{int(h // 24)} day{'s' if h >= 48 else ''}" if h >= 24 and h % 24 == 0 else f"{h:g} hour{'s' if h != 1 else ''}"


def friendly(error: psycopg.Error, table: dict, contract: dict) -> SiteDataError:
    """Rule errors (FORGE_RULE:<rule_id> or a rule's own constraint) and column checks -> a sentence a visitor
    understands. Anything else is a FORGE problem: a general message, never the database's own words."""
    diag = error.diag
    message, constraint = (diag.message_primary or "").strip(), diag.constraint_name or ""
    rules = {r["rule_id"]: r for t in contract.get("tables", []) for r in t.get("rules", [])}
    rule = rules.get(message.removeprefix("FORGE_RULE:")) if message.startswith("FORGE_RULE:") else \
        next((r for r in rules.values() if r.get("object") == constraint), None)
    cols = {c["name"]: c for c in table["columns"]}
    if rule:
        p, k = rule.get("params", {}), rule["kind"]
        if k == "lead_time":                              # built only for its own kind: other rules reuse "hours"
            return SiteDataError(409, f"Please book at least {_hours(float(p['hours']))} ahead." if p.get("hours")
                                 else "That date has already passed. Please pick a later one.")
        if k == "max_advance":
            return SiteDataError(409, f"Bookings open {int(p.get('days', 0))} days ahead. Please pick an earlier date.")
        texts = {
            "no_overlap": "That time is already taken. Please pick another.",
            "within_hours": "We're closed at that time. Please pick a time within our opening hours.",
            "capacity": "Sorry, this one is full.",
            "unique_together": "You've already booked this one.",
            "status_flow": "That change of status is not allowed.",
        }
        if k in texts:
            return SiteDataError(409, texts[k])
        field = p.get("field") or p.get("end")
        if k == "required_if" and field in cols:
            return SiteDataError(422, f"Please fill in '{_label(cols[field])}'.", field)
        return SiteDataError(422, f"Please check '{_label(cols[field])}'." if field in cols
                             else "Please check the details you entered.", field)
    if isinstance(error, psycopg.errors.NotNullViolation) and diag.column_name in cols:
        return SiteDataError(422, f"Please fill in '{_label(cols[diag.column_name])}'.", diag.column_name)
    if isinstance(error, (psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation)):
        col = next((c for c in table["columns"] if constraint.endswith(f"__{c['name']}")), None)
        if col:
            return SiteDataError(422, f"Please choose a valid {_label(col).lower()}.", col["name"])
        return SiteDataError(409, "This is still used elsewhere, so it cannot be removed.")
    if isinstance(error, psycopg.errors.UniqueViolation):
        col = next((c for c in table["columns"] if c["name"] in constraint), None)
        return SiteDataError(409, f"This {_label(col).lower()} is already registered." if col
                             else "This was already sent.", col["name"] if col else None)
    if isinstance(error, psycopg.errors.CheckViolation):
        col = next((c for c in table["columns"] if f"__{c['name']}_" in constraint), None)
        return SiteDataError(422, f"Please check '{_label(col)}'." if col else "Please check the details you entered.",
                             col["name"] if col else None)
    return SiteDataError(500, "Something went wrong on our side. Please try again.")


# ---------------------------------------------------------------- queries (always as the site's own role)
def _as_site(conn, storage: Storage) -> None:
    conn.execute(f"SET LOCAL ROLE {ident(storage.role)}")
    conn.execute(f"SET LOCAL search_path TO {ident(storage.schema)}")


def _json(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


@contextmanager
def _site_tx(storage: Storage, conn=None) -> Iterator:
    """A transaction as the site's role: on a pooled connection, or as a savepoint on `conn` (the backend gate runs
    everything inside one transaction it rolls back)."""
    if conn is None:
        with pool().connection() as c, c.transaction():
            _as_site(c, storage)
            yield c
    else:
        with conn.transaction():
            _as_site(conn, storage)
            yield conn


def submit(storage: Storage, table_name: str, payload: Any, conn=None) -> dict:
    """Save one visitor submission (and an order's items) in one transaction. Returns {id, status, message}."""
    table = storage.table(table_name)
    if not table or table["role"] != "submission" or _is_child(storage, table):
        raise SiteDataError(404, "This site does not take that form.")
    values = check_submission(table, payload, storage.tz)
    children = _children(storage, table)
    items = payload.get("items") if isinstance(payload, dict) else None
    if children and items is not None and not (isinstance(items, list) and 0 < len(items) <= 50):
        raise SiteDataError(422, "Please add between 1 and 50 items.")
    try:
        with _site_tx(storage, conn) as conn:
            row = _insert(conn, storage, table, values, ["id", "status"] if _has(table, "status") else ["id"])
            for child, link in children:
                for item in items or []:
                    item = {k: v for k, v in item.items() if k != link} if isinstance(item, dict) else item
                    clean = check_submission(child, item, storage.tz, frozenset({link}))
                    _insert(conn, storage, child, {**clean, link: row["id"]}, ["id"])
    except psycopg.Error as error:
        raise friendly(error, table, storage.contract) from error
    status = row.get("status")
    message = "You're on the waitlist; we'll let you know." if status == "Waitlist" else None
    return {"id": str(row["id"]), "status": status, "message": message}


def _insert(conn, storage: Storage, table: dict, values: dict, returning: list[str]) -> dict:
    cols = list(values)
    sql = (f"INSERT INTO {ident(storage.schema)}.{ident(table['name'])} ({', '.join(ident(c) for c in cols)}) "
           f"VALUES ({', '.join(['%s'] * len(cols))}) RETURNING {', '.join(ident(c) for c in returning)}") if cols else \
        f"INSERT INTO {ident(storage.schema)}.{ident(table['name'])} DEFAULT VALUES RETURNING {', '.join(ident(c) for c in returning)}"
    return dict(zip(returning, conn.execute(sql, [values[c] for c in cols]).fetchone()))


def _has(table: dict, column: str) -> bool:
    return any(c["name"] == column for c in table["columns"])


def _links_to(child: dict, parent: str) -> str | None:
    return next((c["name"] for c in child["columns"] if c["type"] == "reference" and c.get("reference") == parent
                 and c["required"]), None)


def _children(storage: Storage, table: dict) -> list[tuple[dict, str]]:
    """Submission tables that belong to this one (order_items of orders): sent as the payload's `items`."""
    out = []
    for t in storage.contract.get("tables", []):
        link = _links_to(t, table["name"])
        if t["role"] == "submission" and link and not _has(t, "status"):
            out.append((t, link))
    return out


def _is_child(storage: Storage, table: dict) -> bool:
    return not _has(table, "status") and any(_links_to(table, t["name"]) for t in storage.contract.get("tables", [])
                                             if t["role"] == "submission" and t["name"] != table["name"])


def list_public(storage: Storage, table_name: str, conn=None) -> list[dict]:
    """A public list for the site (services, stylists, class times): never visitor submissions, never personal
    fields, never rows the owner hid; at most 200 rows."""
    table = storage.table(table_name)
    if not table or table["role"] not in ("catalogue", "setting"):
        raise SiteDataError(404, "This site has no such list.")
    cols = ["id"] + [c["name"] for c in table["columns"] if not c["personal"] and not
                     (c["type"] == "reference" and c.get("multiple"))]
    hidden = [f for f in HIDDEN_FLAGS if any(c["name"] == f and c["type"] == "boolean" for c in table["columns"])]
    where = " AND ".join(f"{ident(f)} IS NOT FALSE" for f in hidden) or "true"
    with _site_tx(storage, conn) as conn:
        rows = conn.execute(f"SELECT {', '.join(ident(c) for c in cols)} FROM {ident(storage.schema)}."
                            f"{ident(table['name'])} WHERE {where} ORDER BY created_at LIMIT {LIST_LIMIT}").fetchall()
    return [{c: _json(v) for c, v in zip(cols, r)} for r in rows]


# ---------------------------------------------------------------- free times for a booking form
STEP_MINUTES = 30            # shortcut: slots every 30 minutes; use each service's length when owners ask for it
DEFAULT_HOURS = (time(9, 0), time(18, 0))     # when the owner has not set working hours yet (the rule allows all)


def booking_rules(table: dict) -> dict[str, dict]:
    """The time rules of a booking table, by kind (no_overlap, within_hours, end_from_duration, lead_time...)."""
    return {r["kind"]: r.get("params", {}) for r in table.get("rules", [])}


def availability(storage: Storage, table_name: str, day: str, choices: dict[str, str], conn=None) -> list[str]:
    """Free start times ("HH:MM", site time) on `day` for a booking table: inside working hours, not on a day off,
    not overlapping a booking that still counts, and inside the notice rules. `choices`: the visitor's picks that
    matter (e.g. staff_id, service_id). The database re-checks every booking, so this is only a helper."""
    table = storage.table(table_name)
    rules = booking_rules(table) if table else {}
    timing = rules.get("no_overlap") or rules.get("within_hours")
    if not table or table["role"] != "submission" or not timing:
        raise SiteDataError(404, "This form has no times to choose from.")
    try:
        when = date.fromisoformat(day)
    except ValueError:
        raise SiteDataError(422, "Please pick a date.") from None
    start, end = timing["start"], timing.get("end")
    resource = (rules.get("no_overlap") or {}).get("resource") or (rules.get("within_hours") or {}).get("resource")
    tz, now = storage.tz, datetime.now(storage.tz)
    lead = timedelta(hours=float((rules.get("lead_time") or {}).get("hours") or 0))
    advance = (rules.get("max_advance") or {}).get("days")
    if when < now.date() or (advance and when > now.date() + timedelta(days=int(advance))):
        return []
    rid = _uuid(choices.get(resource)) if resource else None
    with _site_tx(storage, conn) as c:
        opens, closes = DEFAULT_HOURS
        hours = rules.get("within_hours")
        if hours:
            hours_table = storage.table(hours["hours"])
            own = resource and hours_table and _has(hours_table, resource) and rid
            rows = c.execute(
                f"SELECT opens, closes, {ident(resource) + ' IS NOT NULL' if own else 'false'} AS mine FROM "
                f"{ident(storage.schema)}.{ident(hours['hours'])} WHERE day = %s"
                + (f" AND ({ident(resource)} IS NULL OR {ident(resource)} = %s)" if own else ""),
                [when.strftime("%A")] + ([rid] if own else [])).fetchall()
            any_hours = c.execute(f"SELECT 1 FROM {ident(storage.schema)}.{ident(hours['hours'])} LIMIT 1").fetchone()
            if any_hours:
                if not rows:
                    return []                             # closed that day
                opens, closes, _ = sorted(rows, key=lambda r: not r[2])[0]   # the staff member's own hours first
            off = hours.get("days_off") and storage.table(hours["days_off"])
            if off:
                mine = resource and _has(off, resource) and rid
                if c.execute(f"SELECT 1 FROM {ident(storage.schema)}.{ident(off['name'])} WHERE date = %s"
                             + (f" AND ({ident(resource)} IS NULL OR {ident(resource)} = %s)" if mine else ""),
                             [when] + ([rid] if mine else [])).fetchone():
                    return []
        length = timedelta(minutes=STEP_MINUTES)
        duration = rules.get("end_from_duration")
        via_id = _uuid(choices.get(duration["via"])) if duration else None
        if duration and via_id:
            parent = next((t["name"] for t in storage.contract["tables"] for col in table["columns"]
                           if col["name"] == duration["via"] and col.get("reference") == t["name"]), None)
            got = parent and c.execute(f"SELECT {ident(duration['duration'])} FROM {ident(storage.schema)}."
                                       f"{ident(parent)} WHERE id = %s", [via_id]).fetchone()
            if got and got[0]:
                length = timedelta(minutes=int(got[0]))
        ignore = (rules.get("no_overlap") or {}).get("ignore_statuses") or []
        taken = []
        if rules.get("no_overlap") and end:
            same = f" AND {ident(resource)} = %s" if resource and rid else ""
            skip = f" AND status <> ALL(%s)" if ignore and _has(table, "status") else ""
            taken = c.execute(
                f"SELECT {ident(start)}, {ident(end)} FROM {ident(storage.schema)}.{ident(table['name'])} "
                f"WHERE {ident(start)} < %s AND {ident(end)} > %s{same}{skip}",
                [datetime.combine(when + timedelta(days=1), time(0), tz), datetime.combine(when, time(0), tz)]
                + ([rid] if same else []) + ([ignore] if skip else [])).fetchall()
    out, slot = [], datetime.combine(when, opens, tz)
    last = datetime.combine(when, closes, tz)
    while slot + length <= last:
        if slot >= now + lead and not any(a < slot + length and b > slot for a, b in taken):
            out.append(slot.strftime("%H:%M"))
        slot += timedelta(minutes=STEP_MINUTES)
    return out


def _uuid(value) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value)) if value else None
    except ValueError:
        raise SiteDataError(422, "Please choose a valid option.") from None


# ---------------------------------------------------------------- the owner's dashboard (D-250)
PAGE_SIZE = 50
OWNER_LISTS = ("catalogue", "setting")


def _owner_table(storage: Storage, name: str) -> dict:
    table = storage.table(name)
    if not table:
        raise SiteDataError(404, "This site has no such list.")
    return table


def _status_moves(table: dict) -> dict[str, list[str]]:
    return next((r.get("params", {}).get("moves", {}) for r in table.get("rules", []) if r["kind"] == "status_flow"), {})


def owner_summary(storage: Storage, conn=None) -> list[dict]:
    """Every list the site keeps, for the owner: what it holds, how many rows, how many came today, and for each
    column how the dashboard shows and edits it."""
    out = []
    today = datetime.now(storage.tz).replace(hour=0, minute=0, second=0, microsecond=0)
    with _site_tx(storage, conn) as c:
        for t in storage.contract.get("tables", []):
            if _is_child(storage, t):
                continue
            total, new = c.execute(f"SELECT count(*), count(*) FILTER (WHERE created_at >= %s AND NOT is_sample) "
                                   f"FROM {ident(storage.schema)}.{ident(t['name'])}", [today]).fetchone()
            out.append({"name": t["name"], "label": t.get("label") or t["name"], "role": t["role"], "rows": total,
                        "new_today": new, "moves": _status_moves(t),
                        "columns": [{k: col.get(k) for k in ("name", "label", "type", "options", "required", "personal",
                                                             "reference", "min", "max", "max_length", "visitor")}
                                    for col in t["columns"] if not (col["type"] == "reference" and col.get("multiple"))]})
    return out


def _label_column(table: dict | None) -> str | None:
    if not table:
        return None
    names = [c["name"] for c in table["columns"]]
    return next((n for n in ("name", "title") if n in names),
                next((c["name"] for c in table["columns"] if c["type"] == "text"), None))


def owner_rows(storage: Storage, table_name: str, page: int = 0, conn=None) -> dict:
    """One page of a list, newest first, with personal data (the owner's own), and the names behind every link."""
    table = _owner_table(storage, table_name)
    cols = ["id", "created_at", "is_sample"] + [c["name"] for c in table["columns"]
                                                 if not (c["type"] == "reference" and c.get("multiple"))]
    links = {c["name"]: c["reference"] for c in table["columns"] if c["type"] == "reference" and not c.get("multiple")}
    with _site_tx(storage, conn) as c:
        rows = c.execute(f"SELECT {', '.join(ident(x) for x in cols)} FROM {ident(storage.schema)}.{ident(table['name'])} "
                         f"ORDER BY created_at DESC, id LIMIT {PAGE_SIZE + 1} OFFSET %s",
                         [max(page, 0) * PAGE_SIZE]).fetchall()
        names = {}
        for col, target in links.items():
            label = _label_column(storage.table(target))
            if label:
                names[col] = {str(i): v for i, v in c.execute(
                    f"SELECT id, {ident(label)} FROM {ident(storage.schema)}.{ident(target)} LIMIT 500").fetchall()}
    return {"rows": [{k: _json(v) for k, v in zip(cols, r)} for r in rows[:PAGE_SIZE]], "more": len(rows) > PAGE_SIZE,
            "names": names}


def owner_update(storage: Storage, table_name: str, row_id: str, payload: Any, conn=None) -> dict:
    """Visitor submissions: only their status changes (the database allows only the listed moves). The owner's own
    lists and settings: any field, checked like a visitor's."""
    table = _owner_table(storage, table_name)
    if not isinstance(payload, dict) or not payload:
        raise SiteDataError(422, "Nothing to change.")
    if table["role"] == "submission" and set(payload) - {"status"}:
        raise SiteDataError(422, "Only the status of what visitors send can be changed.")
    cols = {c["name"]: c for c in table["columns"] if c.get("visitor", True) or c["name"] == "status"}
    values = {}
    for name, raw in payload.items():
        col = cols.get(name)
        if not col or (col["type"] == "reference" and col.get("multiple")):
            raise SiteDataError(422, "This field cannot be changed here.", name)
        if raw is None or raw == "":
            if col["required"]:
                raise SiteDataError(422, f"Please fill in '{_label(col)}'.", name)
            values[name] = None
        else:
            values[name] = check_value(col, raw, storage.tz)
    rid = _uuid(row_id)
    try:
        with _site_tx(storage, conn) as c:
            done = c.execute(f"UPDATE {ident(storage.schema)}.{ident(table['name'])} SET "
                             + ", ".join(f"{ident(k)} = %s" for k in values) + " WHERE id = %s RETURNING id",
                             [*values.values(), rid]).fetchone()
    except psycopg.Error as error:
        raise friendly(error, table, storage.contract) from error
    if not done:
        raise SiteDataError(404, "That row is not there any more.")
    return {"id": str(rid)}


def owner_add(storage: Storage, table_name: str, payload: Any, conn=None) -> dict:
    """A row of the owner's own list or settings (a stylist, a service, opening hours)."""
    table = _owner_table(storage, table_name)
    if table["role"] not in OWNER_LISTS:
        raise SiteDataError(422, "Visitors add these through the site.")
    values = check_submission(table, payload, storage.tz)
    try:
        with _site_tx(storage, conn) as c:
            row = _insert(c, storage, table, values, ["id"])
    except psycopg.Error as error:
        raise friendly(error, table, storage.contract) from error
    return {"id": str(row["id"])}


def owner_delete(storage: Storage, table_name: str, row_id: str, conn=None) -> None:
    """Remove a row of the owner's own list or settings; what visitors sent is never deleted, only cancelled."""
    table = _owner_table(storage, table_name)
    if table["role"] not in OWNER_LISTS:
        raise SiteDataError(422, "What visitors send cannot be deleted; change its status instead.")
    try:
        with _site_tx(storage, conn) as c:
            done = c.execute(f"DELETE FROM {ident(storage.schema)}.{ident(table['name'])} WHERE id = %s RETURNING id",
                             [_uuid(row_id)]).fetchone()
    except psycopg.Error as error:
        raise friendly(error, table, storage.contract) from error
    if not done:
        raise SiteDataError(404, "That row is not there any more.")


def clear_samples(storage: Storage) -> dict:
    """Remove every sample row; the owner's real rows stay. Runs as FORGE (the schema's owner), because the site's
    own role may never delete what visitors sent. Rows that others still link to go in a later pass; a sample row a
    real row still uses (a sample stylist with a real booking) is kept and counted."""
    left, removed, kept = [t["name"] for t in storage.contract.get("tables", [])], 0, 0
    blocked = (psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation)
    with pool().connection() as c, c.transaction():
        for _ in range(len(left) + 1):
            still = []
            for name in left:
                try:
                    with c.transaction():
                        removed += c.execute(f"DELETE FROM {ident(storage.schema)}.{ident(name)} WHERE is_sample").rowcount
                except blocked:
                    still.append(name)
            if not still or still == left:
                left = still
                break
            left = still
        for name in left:                                   # row by row: only the rows still in use stay
            table = f"{ident(storage.schema)}.{ident(name)}"
            for (row,) in c.execute(f"SELECT id FROM {table} WHERE is_sample").fetchall():
                try:
                    with c.transaction():
                        removed += c.execute(f"DELETE FROM {table} WHERE id = %s", (row,)).rowcount
                except blocked:
                    kept += 1
    return {"removed": removed, "kept": kept}
