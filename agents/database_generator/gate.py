# D:\FYP\FORGE-1\agents\database_generator\gate.py
"""
The database gate (D-245): apply the compiled schema and the sample rows in a scratch schema inside one transaction,
try to break every rule, then roll everything back. Nothing stays in the database.

Passing means: the schema and every sample row were accepted (the rules let valid rows in), and for every rule a row
or change that breaks it was refused with that rule's own error (constraint "r_<entity>__<kind>" or
"FORGE_RULE:<rule_id>"). All SQL here is made by code from the plan, so a failure is a FORGE bug, never the model's.
"""
import copy
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import psycopg

from agents.database_generator.compile import Compiled, compile_schema, ident, literal, rule_name
from agents.database_generator.seed import _future_days, _sql_value, seed_rows, seed_sql
from agents.state import DataEntity


@dataclass
class GateResult:
    ok: bool
    tables: int = 0
    rules: int = 0
    tests: list[dict] = field(default_factory=list)      # {rule_id, kind, ok, detail}
    message: str = ""

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t["ok"])


def _insert(schema: str, table: str, row: dict) -> str:
    cols = list(row)
    return (f"INSERT INTO {ident(schema)}.{ident(table)} ({', '.join(ident(c) for c in cols)}) "
            f"VALUES ({', '.join(_sql_value(row[c]) for c in cols)}) RETURNING *")


def _fresh(e: DataEntity, row: dict, keep: set[str] = frozenset(), move: bool = True) -> dict:
    """A copy of a sample row with a new id and new personal/unique values, so only the rule under test can object.
    `move` puts it one week later (same weekday and time), clear of the sample rows' times."""
    new = copy.deepcopy(row)
    if move:
        for r in e.rules:
            start = r.params.get("start")
            if start in new and not r.params.get("via") and isinstance(new[start], (date, datetime)):
                if start not in keep:
                    _shift(e, new, start, new[start] + timedelta(days=7))
    new["id"] = str(uuid.uuid4())
    tag = uuid.uuid4().hex[:6]
    for f in e.fields:
        if f.name in keep or f.name not in new:
            continue
        if f.type == "email":
            new[f.name] = f"test{tag}@example.com"
        elif f.unique and f.type in ("text", "long_text"):
            new[f.name] = f"test {tag}"
    return new


def _refused(conn, sql: str, rule_id: str) -> tuple[bool, str]:
    """Run `sql` in a savepoint; True when it fails with this rule's own error."""
    try:
        with conn.transaction():
            conn.execute(sql)
    except psycopg.Error as error:
        diag = error.diag
        mine = (diag.constraint_name == rule_name(rule_id)
                or (diag.message_primary or "").strip() == f"FORGE_RULE:{rule_id}")
        return mine, f"{diag.sqlstate}: {(diag.message_primary or '')[:120]}"
    return False, "accepted, but it breaks the rule"


def _try(conn, sql: str) -> tuple[list[dict] | None, str]:
    """Run `sql` in a savepoint and return its rows, or None with the error."""
    try:
        with conn.transaction():
            cur = conn.execute(sql)
            names = [c.name for c in cur.description] if cur.description else []
            return [dict(zip(names, r)) for r in cur.fetchall()] if names else [], ""
    except psycopg.Error as error:
        return None, f"{error.diag.sqlstate}: {(error.diag.message_primary or '')[:120]}"


def _working_time(tz: str, after_days: int, hour: int = 11) -> datetime:
    day = _future_days(tz, after_days, 1)[0]
    return datetime.combine(day, time(hour, 0), ZoneInfo(tz))


def _sunday(tz: str) -> date:
    day = datetime.now(ZoneInfo(tz)).date() + timedelta(days=3)
    return day + timedelta(days=(6 - day.weekday()) % 7)


def rule_tests(conn, schema: str, entities: list[DataEntity], rows: dict[str, list[dict]], tz: str) -> list[dict]:
    """One attempt to break each enabled rule; each must be refused with the rule's own error."""
    by_name = {e.name: e for e in entities}
    out = []
    for e in entities:
        base = rows.get(e.name) or []
        for r in e.rules:
            if not r.enabled:
                continue
            try:
                with conn.transaction(force_rollback=True):  # each test starts from the same sample rows
                    ok, detail = _one(conn, schema, e, r, base, rows, by_name, tz)
            except psycopg.Error as error:
                ok, detail = False, f"test could not run: {error.diag.message_primary}"
            out.append({"rule_id": r.rule_id, "kind": r.kind, "ok": ok, "detail": detail})
    return out


def _one(conn, schema, e, r, base, rows, by_name, tz) -> tuple[bool, str]:
    p, k = r.params, r.kind
    if not base:
        return False, "no sample row to test with"
    row = base[0]
    t = f"{ident(schema)}.{ident(e.name)}"

    if k == "unique_together":
        return _refused(conn, _insert(schema, e.name, _fresh(e, row, keep=set(p["fields"]), move=False)), r.rule_id)
    if k == "no_overlap":
        return _refused(conn, _insert(schema, e.name, _fresh(e, row, move=False)), r.rule_id)
    if k == "date_order":
        bad = _fresh(e, row)
        bad[p["end"]] = bad[p["start"]]
        return _refused(conn, _insert(schema, e.name, bad), r.rule_id)
    if k == "range":
        bad = _fresh(e, row)
        bad[p["field"]] = float(p["max"]) + 1
        return _refused(conn, _insert(schema, e.name, bad), r.rule_id)
    if k == "required_if":
        bad = _fresh(e, row)
        when_field = next(f for f in e.fields if f.name == p["when_field"])
        bad[p["when_field"]] = bool(p["when_value"]) if when_field.type == "boolean" else p["when_value"]
        bad[p["field"]] = (not p["equals"]) if "equals" in p else None
        return _refused(conn, _insert(schema, e.name, bad), r.rule_id)
    if k == "status_flow":
        f = next(x for x in e.fields if x.name == p["field"])
        now = row.get(p["field"], f.default)
        allowed = set(p["moves"].get(now, [])) | {now}
        target = next((o for o in f.options if o not in allowed), None)
        if target is None:
            return True, "every move is allowed from the starting status"
        return _refused(conn, f"UPDATE {t} SET {ident(p['field'])} = {literal(target)} WHERE id = {literal(row['id'])}",
                        r.rule_id)
    if k in ("lead_time", "max_advance"):
        if k == "lead_time":                             # inside the notice period; "not in the past" needs the past
            too = datetime.now(ZoneInfo(tz)) + (timedelta(minutes=5) if p["hours"] else timedelta(days=-1))
        else:
            too = _working_time(tz, int(p["days"]) + 3)
        if p.get("via"):
            parent = by_name[next(f.reference for f in e.fields if f.name == p["via"])]
            prow = _fresh(parent, rows[parent.name][0])
            _shift(parent, prow, p["start"], too)
            made, why = _try(conn, _insert(schema, parent.name, prow))
            if made is None:
                return False, f"could not make a test {parent.name} row ({why})"
            bad = _fresh(e, row)
            bad[p["via"]] = prow["id"]
            return _refused(conn, _insert(schema, e.name, bad), r.rule_id)
        bad = _fresh(e, row)
        _shift(e, bad, p["start"], too)
        if k == "lead_time" and isinstance(bad[p["start"]], date) and not isinstance(bad[p["start"]], datetime):
            bad[p["start"]] = datetime.now(ZoneInfo(tz)).date() - timedelta(days=1)
            _shift(e, bad, p["start"], bad[p["start"]])
        return _refused(conn, _insert(schema, e.name, bad), r.rule_id)
    if k == "within_hours":
        bad = _fresh(e, row)
        sunday = datetime.combine(_sunday(tz), time(11, 0), ZoneInfo(tz))
        _shift(e, bad, p["start"], sunday)
        return _refused(conn, _insert(schema, e.name, bad), r.rule_id)
    if k == "end_from_duration":
        made, why = _try(conn, f"SELECT x.{ident(p['end'])} - x.{ident(p['start'])} AS took, d.{ident(p['duration'])} "
                               f"AS mins FROM {t} x JOIN {ident(schema)}.{ident(_ref(e, p['via']))} d "
                               f"ON d.id = x.{ident(p['via'])} WHERE x.id = {literal(row['id'])}")
        if not made:
            return False, f"could not read the sample row ({why})"
        took, mins = made[0]["took"], made[0]["mins"]
        return took == timedelta(minutes=int(mins)), f"end - start = {took}, length {mins} min"
    if k == "capacity":
        return _capacity(conn, schema, e, r, row, rows, by_name)
    return False, f"no test for rule kind {k}"


def _ref(e: DataEntity, field_name: str) -> str:
    return next(f.reference for f in e.fields if f.name == field_name)


def _shift(e: DataEntity, row: dict, start: str, when) -> None:
    """Move a row's start to `when`, keeping its length (end fields of date_order / no_overlap rules)."""
    old = row.get(start)
    row[start] = when.date() if isinstance(old, date) and not isinstance(old, datetime) and isinstance(when, datetime) else when
    for r in e.rules:
        end = r.params.get("end")
        if r.params.get("start") == start and end and end in row and old is not None:
            row[end] = row[start] + (row[end] - old)


def _capacity(conn, schema, e, r, row, rows, by_name) -> tuple[bool, str]:
    p = r.params
    t = f"{ident(schema)}.{ident(e.name)}"
    bad = _fresh(e, row, move=False)
    if p.get("parent"):
        parent = by_name[_ref(e, p["parent"])]
        pt = f"{ident(schema)}.{ident(parent.name)}"
        made, why = _try(conn, f"UPDATE {pt} SET {ident(p['parent_capacity'])} = 1 WHERE id = {literal(row[p['parent']])} RETURNING id")
        if not made:
            return False, f"could not lower the capacity ({why})"
    else:
        bad[p["sum"]] = float(p["max"]) if p.get("sum") else bad.get(p.get("sum", ""), 1)
    if p["overflow"] == "waitlist":
        made, why = _try(conn, _insert(schema, e.name, bad))
        if made is None:
            return False, f"refused instead of waitlisted ({why})"
        status = made[0].get("status")
        return status == "Waitlist", f"status after the place ran out: {status}"
    return _refused(conn, _insert(schema, e.name, bad), r.rule_id)


def run_gate(entities: list[DataEntity], url: str, build_id: str, tz: str = "Asia/Karachi") -> tuple[GateResult, Compiled]:
    """Compile, apply, test, roll back. Returns the result and the compiled files (compiled for the scratch schema;
    provisioning compiles again for the site's own schema)."""
    scratch = f"check_{uuid.uuid5(uuid.NAMESPACE_URL, build_id).hex[:12]}"
    with psycopg.connect(url, connect_timeout=15) as conn:
        gist = bool(conn.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'btree_gist'").fetchone())
        compiled = compile_schema(entities, scratch, tz, gist=gist)
        rows = seed_rows(entities, tz)
        result = GateResult(ok=False, tables=len(entities), rules=len(compiled.rules))
        try:
            with conn.transaction(force_rollback=True):
                conn.execute(compiled.schema_sql)
                try:
                    with conn.transaction():
                        conn.execute(seed_sql(entities, scratch, tz))
                except psycopg.Error as error:
                    result.message = f"the sample rows were refused: {error.diag.message_primary}"
                    return result, compiled
                result.tests = rule_tests(conn, scratch, entities, rows, tz)
        except psycopg.Error as error:
            result.message = f"the schema did not apply: {error.diag.message_primary}"
            return result, compiled
    failed = [t for t in result.tests if not t["ok"]]
    result.ok = not failed
    result.message = (f"{result.tables} tables, {result.rules} rules, {result.passed}/{len(result.tests)} rule tests passed"
                      + (f"; failed: {', '.join(t['rule_id'] for t in failed)}" if failed else ""))
    return result, compiled
