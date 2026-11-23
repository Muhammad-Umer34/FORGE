# D:\FYP\FORGE-1\agents\database_generator\compile.py
"""
The SQL compiler (D-242, D-245): the plan's record types -> PostgreSQL. Code only; no model ever writes SQL.

Every identifier passes the same safety pattern as plan check 26 and is double-quoted; every value goes through
`literal`. Tables are created first and linked afterwards (ALTER TABLE), so the order of record types never
matters. Each rule becomes a named constraint or trigger ("r_<entity>__<kind>"), and every rule failure raises
"FORGE_RULE:<rule_id>" so the Backend Agent can turn it into a friendly message.
"""
import json
import re
from dataclasses import dataclass, field

from agents.planning.data_patterns import NAME, RESERVED
from agents.state import DataEntity, DataField, DataRule

SCHEMA_NAME = re.compile(r"^(site|check)_[a-z0-9_]{1,40}$")
TIMEZONE = re.compile(r"^[A-Za-z]+(/[A-Za-z_+-]+){1,2}$")
SQL_TYPES = {"text": "text", "long_text": "text", "number": "numeric", "money": "numeric(12,2)", "date": "date",
             "time": "time", "datetime": "timestamptz", "email": "text", "phone": "text", "url": "text",
             "boolean": "boolean", "choice": "text", "image": "text", "duration": "integer", "reference": "uuid"}
FORMAT_CHECKS = {"email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$", "phone": r"^[0-9+() .-]{6,24}$",
                 "url": r"^https?://\S+$", "image": r"^(https?://|/)\S+$"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class UnsafeName(ValueError):
    """A name or value code refuses to put into SQL (a bug upstream: plan check 26 should have caught it)."""


def ident(name: str) -> str:
    if not (NAME.match(name) or SCHEMA_NAME.match(name)) or name in RESERVED - {"id", "created_at", "is_sample"}:
        raise UnsafeName(f"unsafe identifier {name!r}")
    return f'"{name}"'


def literal(value) -> str:
    """A SQL literal. Strings are single-quoted with quotes doubled; NUL bytes are refused."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            raise UnsafeName(f"not a finite number: {value!r}")
        return repr(int(value)) if float(value).is_integer() else repr(float(value))
    text = str(value)
    if "\x00" in text:
        raise UnsafeName("NUL byte in a value")
    return "'" + text.replace("'", "''") + "'"


def _array(values: list[str]) -> str:
    return "ARRAY[" + ", ".join(literal(v) for v in values) + "]::text[]"


def rule_name(rule_id: str) -> str:
    """'appointments.no_overlap.2' -> 'r_appointments__no_overlap_2' (a constraint or trigger name, <= 63)."""
    name = "r_" + rule_id.replace(".", "__", 1).replace(".", "_")
    if len(name) > 63:
        raise UnsafeName(f"rule name too long: {name}")
    return name


@dataclass
class Compiled:
    schema_sql: str
    schema_json: dict
    er: str
    rules: list[dict] = field(default_factory=list)      # {rule_id, kind, label, object, error}

    def files(self) -> dict[str, str]:
        return {"db/schema.sql": self.schema_sql, "db/schema.json": json.dumps(self.schema_json, indent=2),
                "db/er.mmd": self.er}


# ---------------------------------------------------------------- columns
def _default(f: DataField) -> str | None:
    if f.default is None:
        return None
    raw = f.default
    if f.type in ("number", "money"):
        return literal(float(raw))
    if f.type == "duration":
        return literal(int(float(raw)))
    if f.type == "boolean":
        if raw.lower() not in ("true", "false"):
            raise UnsafeName(f"boolean default {raw!r}")
        return literal(raw.lower() == "true")
    if f.type == "choice" and raw not in f.options:
        raise UnsafeName(f"default {raw!r} is not an option of {f.name}")
    return literal(raw)


def _column(e: DataEntity, f: DataField) -> tuple[str, list[str]]:
    """(column definition, table checks)."""
    col = ident(f.name)
    sql_type = SQL_TYPES[f.type]
    if f.type == "choice" and f.multiple:
        sql_type = "text[]"
    parts = [col, sql_type]
    if f.required:
        parts.append("NOT NULL")
    if f.unique:
        parts.append("UNIQUE")
    d = _default(f)
    if d is not None:
        parts.append(f"DEFAULT {d}")
    checks = []
    if f.type == "choice":
        if f.multiple:
            checks.append(f"{col} <@ {_array(f.options)}")
        else:
            checks.append(f"{col} IN ({', '.join(literal(o) for o in f.options)})")
    if f.type in FORMAT_CHECKS:
        checks.append(f"{col} ~* {literal(FORMAT_CHECKS[f.type])}")
    if f.type in ("number", "money", "duration"):
        if f.min is not None:
            checks.append(f"{col} >= {literal(f.min)}")
        if f.max is not None:
            checks.append(f"{col} <= {literal(f.max)}")
    if f.max_length and f.type in ("text", "long_text", "email", "phone", "url", "image"):
        checks.append(f"char_length({col}) <= {literal(int(f.max_length))}")
    named = [f"CONSTRAINT {ident(_short(f'f_{e.name}__{f.name}_{n}'))} CHECK ({c})" for n, c in enumerate(checks, 1)]
    return " ".join(parts), named


def _short(name: str) -> str:
    """Field constraint names, kept within PostgreSQL's 63 characters and the identifier pattern."""
    name = re.sub(r"[^a-z0-9_]", "_", name.lower())[:63]
    return name if NAME.match(name) else "f_" + name[:60]


# ---------------------------------------------------------------- rules
class _Rules:
    def __init__(self, schema: str, e: DataEntity, by_name: dict[str, DataEntity], tz: str, gist: bool):
        self.s, self.e, self.by_name, self.tz, self.gist = schema, e, by_name, tz, gist
        self.t = f"{ident(schema)}.{ident(e.name)}"
        self.sql: list[str] = []
        self.made: list[dict] = []

    def field(self, name: str, on: DataEntity | None = None) -> DataField:
        return next(f for f in (on or self.e).fields if f.name == name)

    def parent(self, via: str) -> DataEntity:
        return self.by_name[self.field(via).reference]

    def table(self, e: DataEntity) -> str:
        return f"{ident(self.s)}.{ident(e.name)}"

    def raise_(self, r: DataRule) -> str:
        return f"RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = {literal('FORGE_RULE:' + r.rule_id)}"

    def trigger(self, r: DataRule, order: str, when: str, body: str, declare: str = "") -> str:
        """A BEFORE ROW trigger; `order` sorts triggers (PostgreSQL fires them by name): a_ fills values first."""
        fn = f"{ident(self.s)}.{ident(rule_name(r.rule_id))}"
        name = ident(_short(f"{order}_{rule_name(r.rule_id)}"))
        decl = f"DECLARE\n{declare}" if declare else ""
        self.sql.append(
            f"CREATE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $fn$\n{decl}BEGIN\n{body}\n  RETURN NEW;\nEND\n$fn$;\n"
            f"CREATE TRIGGER {name} BEFORE {when} ON {self.t} FOR EACH ROW EXECUTE FUNCTION {fn}();")
        return rule_name(r.rule_id)

    def statuses(self, values: list[str], column: str = "status") -> str:
        return f"NEW.{ident(column)} IN ({', '.join(literal(v) for v in values)})"

    def add(self, r: DataRule) -> None:
        if not r.enabled:
            return
        p, k = r.params, r.kind
        obj = getattr(self, f"_{k}")(r, p)
        self.made.append({"rule_id": r.rule_id, "kind": k, "label": r.label, "object": obj,
                          "error": f"FORGE_RULE:{r.rule_id}"})

    # -- constraints
    def _unique_together(self, r, p):
        name = rule_name(r.rule_id)
        cols = ", ".join(ident(c) for c in p["fields"])
        where = ""
        if p.get("ignore_statuses"):
            where = f" WHERE {ident('status')} NOT IN ({', '.join(literal(v) for v in p['ignore_statuses'])})"
        self.sql.append(f"CREATE UNIQUE INDEX {ident(name)} ON {self.t} ({cols}){where};")
        return name

    def _range(self, r, p):
        name = rule_name(r.rule_id)
        c = ident(p["field"])
        self.sql.append(f"ALTER TABLE {self.t} ADD CONSTRAINT {ident(name)} CHECK "
                        f"({c} IS NULL OR {c} BETWEEN {literal(p['min'])} AND {literal(p['max'])});")
        return name

    def _required_if(self, r, p):
        name = rule_name(r.rule_id)
        f, w = ident(p["field"]), ident(p["when_field"])
        when_value = p["when_value"]
        wf = self.field(p["when_field"])
        cond = f"{w} IS DISTINCT FROM {literal(when_value if wf.type != 'boolean' else bool(when_value))}"
        need = f"{f} IS NOT NULL" + (f" AND {f} = {literal(p['equals'])}" if "equals" in p else "")
        self.sql.append(f"ALTER TABLE {self.t} ADD CONSTRAINT {ident(name)} CHECK ({cond} OR ({need}));")
        return name

    def _date_order(self, r, p):
        name = rule_name(r.rule_id)
        s, t = ident(p["start"]), ident(p["end"])
        days = p.get("min_days")
        cond = (f"{t} - {s} >= {literal(int(days))}" if days and self.field(p["start"]).type == "date"
                else f"{t} > {s}")
        self.sql.append(f"ALTER TABLE {self.t} ADD CONSTRAINT {ident(name)} CHECK ({s} IS NULL OR {t} IS NULL OR {cond});")
        return name

    def _range_expr(self, p, row: str = "") -> str:
        s, t = f"{row}{ident(p['start'])}", f"{row}{ident(p['end'])}"
        return (f"daterange({s}, {t}, '[]')" if self.field(p["start"]).type == "date"
                else f"tstzrange({s}, {t}, '[)')")

    def _no_overlap(self, r, p):
        name = rule_name(r.rule_id)
        ignore = p.get("ignore_statuses") or []
        if self.gist:
            cols = ([f"{ident(p['resource'])} WITH ="] if p.get("resource") else []) + [f"{self._range_expr(p)} WITH &&"]
            where = (f" WHERE ({ident('status')} NOT IN ({', '.join(literal(v) for v in ignore)}))" if ignore else "")
            self.sql.append(f"ALTER TABLE {self.t} ADD CONSTRAINT {ident(name)} EXCLUDE USING gist ({', '.join(cols)}){where};")
            return name
        same = f"x.{ident(p['resource'])} IS NOT DISTINCT FROM NEW.{ident(p['resource'])} AND " if p.get("resource") else ""
        skip = f" AND x.{ident('status')} NOT IN ({', '.join(literal(v) for v in ignore)})" if ignore else ""
        mine = f"NEW.{ident('status')} NOT IN ({', '.join(literal(v) for v in ignore)})" if ignore else "true"
        lock = f"hashtext({literal(r.rule_id)} || coalesce(NEW.{ident(p['resource'])}::text, ''))" if p.get("resource") \
            else f"hashtext({literal(r.rule_id)})"
        body = (f"  IF {mine} THEN\n    PERFORM pg_advisory_xact_lock({lock});\n"
                f"    IF EXISTS (SELECT 1 FROM {self.t} x WHERE x.id <> NEW.id AND {same}"
                f"{self._range_expr(p, 'x.')} && {self._range_expr(p, 'NEW.')}{skip}) THEN\n      {self.raise_(r)};\n"
                f"    END IF;\n  END IF;")
        return self.trigger(r, "c", "INSERT OR UPDATE", body)

    # -- triggers
    def _end_from_duration(self, r, p):
        parent = self.parent(p["via"])
        body = (f"  IF NEW.{ident(p['start'])} IS NOT NULL THEN\n"
                f"    SELECT NEW.{ident(p['start'])} + make_interval(mins => d.{ident(p['duration'])}) INTO NEW.{ident(p['end'])}\n"
                f"      FROM {self.table(parent)} d WHERE d.id = NEW.{ident(p['via'])};\n  END IF;")
        return self.trigger(r, "a", "INSERT OR UPDATE", body)

    def _capacity(self, r, p):
        counted = p.get("count_statuses") or []
        add = f"coalesce(NEW.{ident(p['sum'])}, 1)" if p.get("sum") else "1"
        summed = f"coalesce(sum(x.{ident(p['sum'])}), 0)" if p.get("sum") else "count(*)"
        in_count = f"x.{ident('status')} IN ({', '.join(literal(v) for v in counted)})" if counted else "true"
        mine = self.statuses(counted) if counted else "true"
        if p["overflow"] == "waitlist":
            over = f"NEW.{ident('status')} := 'Waitlist';"
        else:
            over = f"{self.raise_(r)};"
        if p.get("parent"):
            parent = self.parent(p["parent"])
            cap = ident(p["parent_capacity"])
            key = ident(p["parent"])
            body = (f"  IF {mine} THEN\n"
                    f"    SELECT d.{cap} INTO cap FROM {self.table(parent)} d WHERE d.id = NEW.{key} FOR UPDATE;\n"
                    f"    IF cap IS NOT NULL THEN\n"
                    f"      SELECT {summed} INTO used FROM {self.t} x WHERE x.{key} = NEW.{key} AND x.id <> NEW.id AND {in_count};\n"
                    f"      IF used + {add} > cap THEN\n        {over}\n      END IF;\n    END IF;\n  END IF;")
        else:
            group = p["group_by"]
            same = " AND ".join(f"x.{ident(g)} IS NOT DISTINCT FROM NEW.{ident(g)}" for g in group)
            lock = " || ".join([literal(r.rule_id)] + [f"coalesce(NEW.{ident(g)}::text, '')" for g in group])
            body = (f"  IF {mine} THEN\n    PERFORM pg_advisory_xact_lock(hashtext({lock}));\n"
                    f"    cap := {literal(p['max'])};\n"
                    f"    SELECT {summed} INTO used FROM {self.t} x WHERE {same} AND x.id <> NEW.id AND {in_count};\n"
                    f"    IF used + {add} > cap THEN\n      {over}\n    END IF;\n  END IF;")
        return self.trigger(r, "b", "INSERT OR UPDATE", body, "  cap numeric;\n  used numeric;\n")

    def _within_hours(self, r, p):
        hours, off = self.by_name[p["hours"]], self.by_name.get(p.get("days_off") or "")
        res = p.get("resource")
        tz = literal(self.tz)
        start, end = f"(NEW.{ident(p['start'])} AT TIME ZONE {tz})", f"(NEW.{ident(p['end'])} AT TIME ZONE {tz})"
        who_h = (f" AND (h.{ident(res)} IS NULL OR h.{ident(res)} = NEW.{ident(res)})"
                 if res and any(f.name == res for f in hours.fields) else "")
        who_d = (f" AND (o.{ident(res)} IS NULL OR o.{ident(res)} = NEW.{ident(res)})"
                 if res and off and any(f.name == res for f in off.fields) else "")
        days_off = (f"    IF EXISTS (SELECT 1 FROM {self.table(off)} o WHERE o.{ident('date')} = {start}::date{who_d}) THEN\n"
                    f"      {self.raise_(r)};\n    END IF;\n") if off else ""
        body = (f"  IF NEW.{ident(p['start'])} IS NOT NULL AND EXISTS (SELECT 1 FROM {self.table(hours)}) THEN\n"
                f"{days_off}"
                f"    IF {end}::date <> {start}::date OR NOT EXISTS (SELECT 1 FROM {self.table(hours)} h\n"
                f"        WHERE h.{ident('day')} = trim(to_char({start}, 'FMDay')){who_h}\n"
                f"          AND {start}::time >= h.{ident('opens')} AND {end}::time <= h.{ident('closes')}) THEN\n"
                f"      {self.raise_(r)};\n    END IF;\n  END IF;")
        return self.trigger(r, "c", "INSERT OR UPDATE", body)

    def _start_value(self, p) -> tuple[str, str, str]:
        """(expression, declare, lookup) for a rule's start time, on this row or on the linked row."""
        if p.get("via"):
            parent = self.parent(p["via"])
            kind = self.field(p["start"], parent).type
            lookup = (f"  SELECT d.{ident(p['start'])} INTO start_value FROM {self.table(parent)} d "
                      f"WHERE d.id = NEW.{ident(p['via'])};\n")
            return "start_value", f"  start_value {SQL_TYPES[kind]};\n", lookup
        return f"NEW.{ident(p['start'])}", "", ""

    def _time_rule(self, r, p, op: str, amount: str):
        value, declare, lookup = self._start_value(p)
        kind = (self.field(p["start"], self.parent(p["via"])) if p.get("via") else self.field(p["start"])).type
        now = f"(now() AT TIME ZONE {literal(self.tz)})"
        bound = (f"({now} + {amount})::date" if kind == "date" else f"now() + {amount}")
        body = f"{lookup}  IF {value} IS NOT NULL AND {value} {op} {bound} THEN\n    {self.raise_(r)};\n  END IF;"
        return self.trigger(r, "c", "INSERT", body, declare)

    def _lead_time(self, r, p):
        return self._time_rule(r, p, "<", f"make_interval(mins => {literal(int(round(float(p['hours']) * 60)))})")

    def _max_advance(self, r, p):
        return self._time_rule(r, p, ">", f"make_interval(days => {literal(int(p['days']))})")

    def _status_flow(self, r, p):
        col = ident(p["field"])
        moves = p["moves"]
        pairs = [(a, b) for a, bs in moves.items() for b in bs]
        allowed = " OR ".join(f"(OLD.{col} = {literal(a)} AND NEW.{col} = {literal(b)})" for a, b in pairs) or "false"
        f = self.field(p["field"])
        starts = list(dict.fromkeys(([f.default] if f.default else []) + list(moves)))
        if any(x.kind == "capacity" and x.params.get("overflow") == "waitlist" for x in self.e.rules):
            starts.append("Waitlist")
        body = (f"  IF TG_OP = 'INSERT' THEN\n    IF NEW.{col} NOT IN ({', '.join(literal(s) for s in dict.fromkeys(starts))}) THEN\n"
                f"      {self.raise_(r)};\n    END IF;\n"
                f"  ELSIF NEW.{col} IS DISTINCT FROM OLD.{col} AND NOT ({allowed}) THEN\n    {self.raise_(r)};\n  END IF;")
        return self.trigger(r, "d", "INSERT OR UPDATE", body)


# ---------------------------------------------------------------- the whole schema
def compile_schema(entities: list[DataEntity], schema: str, tz: str = "Asia/Karachi", gist: bool = True) -> Compiled:
    """Record types -> one SQL script that creates the schema (run inside a transaction), plus its JSON contract
    and a Mermaid ER diagram. Raises UnsafeName for anything that should have been caught by the plan checks."""
    if not SCHEMA_NAME.match(schema):
        raise UnsafeName(f"unsafe schema name {schema!r}")
    if not TIMEZONE.match(tz):
        raise UnsafeName(f"unsafe time zone {tz!r}")
    by_name = {e.name: e for e in entities}
    sch = ident(schema)
    uses_gist = gist and any(r.kind == "no_overlap" and r.enabled and r.params.get("resource")
                             for e in entities for r in e.rules)
    out = [f"-- FORGE generated schema (D-242). Written by code from the plan; do not edit by hand.",
           *(["CREATE EXTENSION IF NOT EXISTS btree_gist;"] if uses_gist else []),
           f"CREATE SCHEMA {sch};"]
    links, joins, comments, rules_sql, made = [], [], [], [], []
    for e in entities:
        t = f"{sch}.{ident(e.name)}"
        cols = ["\"id\" uuid PRIMARY KEY DEFAULT gen_random_uuid()",
                "\"created_at\" timestamptz NOT NULL DEFAULT now()",
                "\"is_sample\" boolean NOT NULL DEFAULT false"]
        checks = []
        for f in e.fields:
            if f.type == "reference" and f.multiple:
                target = by_name[f.reference]
                jt = f"{sch}.{ident(_short(f'{e.name}__{f.name}'))}"
                a, b = ident(_short(f"{e.name}_id")), ident(_short(f"{f.name}_id"))
                joins.append(f"CREATE TABLE {jt} (\n  {a} uuid NOT NULL REFERENCES {t} (id) ON DELETE CASCADE,\n"
                             f"  {b} uuid NOT NULL REFERENCES {sch}.{ident(target.name)} (id) ON DELETE CASCADE,\n"
                             f"  PRIMARY KEY ({a}, {b})\n);")
                continue
            col, named = _column(e, f)
            cols.append(col)
            checks += named
            if f.type == "reference":
                action = {"restrict": "RESTRICT", "cascade": "CASCADE", "set_null": "SET NULL"}[f.on_delete]
                links.append(f"ALTER TABLE {t} ADD CONSTRAINT {ident(_short(f'l_{e.name}__{f.name}'))} FOREIGN KEY "
                             f"({ident(f.name)}) REFERENCES {sch}.{ident(f.reference)} (id) ON DELETE {action};")
                links.append(f"CREATE INDEX ON {t} ({ident(f.name)});")
            if f.label:
                comments.append(f"COMMENT ON COLUMN {t}.{ident(f.name)} IS "
                                f"{literal(f.label + (' (personal)' if f.personal else ''))};")
        out.append(f"CREATE TABLE {t} (\n  " + ",\n  ".join(cols + checks) + "\n);")
        if any(f.name == "status" for f in e.fields):
            links.append(f"CREATE INDEX ON {t} (\"status\");")
        comments.append(f"COMMENT ON TABLE {t} IS {literal(e.label or e.name)};")
        rules = _Rules(schema, e, by_name, tz, gist)
        for r in e.rules:
            rules.add(r)
        rules_sql += rules.sql
        made += rules.made
    starts = {(e.name, r.params["start"]) for e in entities for r in e.rules
              if r.enabled and r.params.get("start") and not r.params.get("via")}
    links += [f"CREATE INDEX ON {sch}.{ident(t)} ({ident(c)});" for t, c in sorted(starts)]
    sql = "\n\n".join(out + joins + links + rules_sql + comments) + "\n"
    return Compiled(schema_sql=sql, schema_json=_contract(entities, schema, made, tz), er=er_diagram(entities),
                    rules=made)


def _contract(entities: list[DataEntity], schema: str, made: list[dict], tz: str) -> dict:
    """db/schema.json: what the Backend Agent reads (tables, columns, links, rules and their error names)."""
    by_rule = {m["rule_id"]: m for m in made}
    return {"schema": schema, "time_zone": tz, "tables": [{
        "name": e.name, "label": e.label, "role": e.role, "pattern": e.pattern,
        "columns": [{"name": f.name, "label": f.label, "type": f.type, "required": f.required, "personal": f.personal,
                     "options": f.options, "multiple": f.multiple, "reference": f.reference, "default": f.default,
                     "min": f.min, "max": f.max, "max_length": f.max_length} for f in e.fields],
        "rules": [by_rule[r.rule_id] for r in e.rules if r.rule_id in by_rule]} for e in entities]}


def er_diagram(entities: list[DataEntity]) -> str:
    """A Mermaid ER diagram made by rules (most of FR-13 at no model cost)."""
    lines = ["erDiagram"]
    for e in entities:
        lines.append(f"  {e.name} {{")
        lines.append("    uuid id PK")
        for f in e.fields:
            if f.type == "reference" and f.multiple:
                continue
            kind = SQL_TYPES[f.type].split("(")[0].replace(" ", "_")
            key = " FK" if f.type == "reference" else ""
            lines.append(f"    {kind} {f.name}{key}")
        lines.append("  }")
    for e in entities:
        for f in e.fields:
            if f.type != "reference":
                continue
            if f.multiple:
                lines.append(f'  {e.name} }}o--o{{ {f.reference} : "{f.label or f.name}"')
            else:
                many = "||" if f.required else "|o"
                lines.append(f'  {f.reference} {many}--o{{ {e.name} : "{f.label or f.name}"')
    return "\n".join(lines) + "\n"
