# D:\FYP\FORGE-1\agents\database_generator\seed.py
"""
Sample rows for the preview (D-242): a few rows in every record type, marked is_sample, written so they pass every
rule (future times inside working hours, no overlaps, within capacity). Code only. The owner's real business details
replace the catalogue rows later; a published site deletes the sample rows (FYP-2).
"""
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from agents.database_generator.compile import DAYS, ident, literal
from agents.state import DataEntity, DataField

OPEN, CLOSE = time(9, 0), time(18, 0)


def _future_days(tz: str, start_after: int, count: int) -> list[date]:
    """Working days (Monday to Saturday) far enough ahead to pass any lead time FORGE offers (at most 2 days)."""
    day = datetime.now(ZoneInfo(tz)).date() + timedelta(days=start_after)
    out = []
    while len(out) < count:
        if day.weekday() < 6:
            out.append(day)
        day += timedelta(days=1)
    return out


def _value(e: DataEntity, f: DataField, n: int, ids: dict[str, list[str]], when: datetime, day: date):
    """A valid sample value for field `f` on row `n` (1-based)."""
    if f.type == "reference":
        targets = ids.get(f.reference or "", [])
        return targets[(n - 1) % len(targets)] if targets else None
    if f.default is not None and f.type not in ("text", "long_text"):
        if f.type == "boolean":
            return f.default.lower() == "true"
        if f.type in ("number", "money", "duration"):
            return float(f.default)
        return f.default
    t = f.type
    if t == "choice":
        return [f.options[0]] if f.multiple else f.options[0]
    if t == "email":
        return f"sample{n}@example.com"
    if t == "phone":
        return f"0300 000000{n}"
    if t in ("url", "image"):
        return f"https://example.com/sample-{n}" + (".jpg" if t == "image" else "")
    if t == "boolean":
        return True
    if t == "money":
        return float(1000 * n)
    if t == "duration":
        return 30.0
    if t == "number":
        low = f.min if f.min is not None else 1
        high = f.max if f.max is not None else low + 10
        return float(min(max(low, 2), high))
    if t == "date":
        return day
    if t == "time":
        return time(10 + n, 0)
    if t == "datetime":
        return when
    label = (f.label or f.name.replace("_", " ")).strip()
    if t == "long_text":
        return f"Sample {label.lower()}: replace this with your own words."
    text = f"Sample {label.lower()} {n}"
    return text[: f.max_length] if f.max_length else text


def seed_rows(entities: list[DataEntity], tz: str = "Asia/Karachi") -> dict[str, list[dict]]:
    """Rows by record type, parents before children, with fixed ids so links can point at them."""
    zone = ZoneInfo(tz)
    days = _future_days(tz, 3, 12)
    by_name = {e.name: e for e in entities}
    order, seen = [], set()

    def visit(e: DataEntity) -> None:
        if e.name in seen:
            return
        seen.add(e.name)
        for f in e.fields:
            if f.reference and f.reference in by_name and f.reference != e.name:
                visit(by_name[f.reference])
        order.append(e)

    for e in entities:
        visit(e)
    ids: dict[str, list[str]] = {}
    rows: dict[str, list[dict]] = {}
    for e in order:
        if e.name == "working_hours" or {"day", "opens", "closes"} <= {f.name for f in e.fields}:
            made = [{"day": d, "opens": OPEN, "closes": CLOSE} for d in DAYS[:6]]          # Monday to Saturday
        elif {"date"} == {f.name for f in e.fields if f.required and f.type == "date"} and "days_off" in e.name:
            made = [{"date": _future_days(tz, 40, 1)[0] + timedelta(days=6 - _future_days(tz, 40, 1)[0].weekday())}]
        else:
            made = []
            for n in range(1, (e.sample_rows or 3) + 1):
                day = days[(n - 1) * 2 % len(days)]
                when = datetime.combine(day, time(10 + n, 0), zone)
                row = {}
                for f in e.fields:
                    if f.type == "reference" and f.multiple:
                        continue
                    if not f.required and f.type == "reference":
                        continue                     # optional links stay empty (any stylist, everyone's hours)
                    v = _value(e, f, n, ids, when, day)
                    if v is not None:
                        row[f.name] = v
                _fit_rules(e, row, when, day)
                made.append(row)
        for r in made:
            r["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"forge-sample/{e.name}/{len(ids.get(e.name, []))}"))
            ids.setdefault(e.name, []).append(r["id"])
        rows[e.name] = made
    return rows


def _fit_rules(e: DataEntity, row: dict, when: datetime, day: date) -> None:
    """Small fixes so a sample row passes its record type's rules."""
    for r in e.rules:
        p = r.params
        if r.kind == "date_order" and p.get("start") in row:
            start = row[p["start"]]
            gap = max(int(p.get("min_days") or 0), 1)
            if isinstance(start, datetime):
                row[p["end"]] = start + timedelta(hours=1)
            elif isinstance(start, date):
                row[p["end"]] = start + timedelta(days=gap)
            elif isinstance(start, time):
                row[p["end"]] = time(min(start.hour + 1, 23), start.minute)
        if r.kind == "end_from_duration":
            row[p["end"]] = when + timedelta(minutes=30)      # the trigger sets the real value from the service
        if r.kind == "no_overlap" and p.get("start") in row and p.get("end") not in row:
            row[p["end"]] = row[p["start"]] + (timedelta(hours=1) if isinstance(row[p["start"]], datetime)
                                               else timedelta(days=1))


def seed_sql(entities: list[DataEntity], schema: str, tz: str = "Asia/Karachi") -> str:
    """db/seed.sql: INSERTs with literal values only, all marked is_sample."""
    lines = ["-- FORGE sample rows for the preview (is_sample = true). Written by code."]
    for name, made in seed_rows(entities, tz).items():
        for row in made:
            cols = ["is_sample", *row.keys()]
            vals = [literal(True)] + [_sql_value(v) for v in row.values()]
            lines.append(f"INSERT INTO {ident(schema)}.{ident(name)} ({', '.join(ident(c) for c in cols)}) "
                         f"VALUES ({', '.join(vals)});")
    return "\n".join(lines) + "\n"


def _sql_value(v) -> str:
    if isinstance(v, datetime):
        return literal(v.isoformat()) + "::timestamptz"
    if isinstance(v, date):
        return literal(v.isoformat()) + "::date"
    if isinstance(v, time):
        return literal(v.strftime("%H:%M")) + "::time"
    if isinstance(v, list):
        return "ARRAY[" + ", ".join(literal(x) for x in v) + "]::text[]"
    return literal(v)
