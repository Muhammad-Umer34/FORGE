# D:\FYP\FORGE-1\agents\planning\data_patterns.py
"""
Data recipes (D-242): components/data_patterns.json lists record types, fields and rules for the kinds of data small
business sites keep (messages, time bookings, sessions with seats, orders and quotes, catalogues, applications).
The model only picks recipes, switch values, extra fields and names; this module expands them into the plan's data
model, writes each rule's plain-English sentence, and checks that a data model only uses what code can compile.
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from agents.state import DataEntity, DataField, DataRule

PATTERNS_FILE = Path(__file__).resolve().parents[2] / "components" / "data_patterns.json"
NAME = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
# Words PostgreSQL or our generated code reserve; a table or field may not use them (planning check 26).
RESERVED = {"all", "and", "any", "array", "as", "asc", "between", "by", "case", "cast", "check", "collate", "column",
            "constraint", "create", "created_at", "current_date", "current_time", "current_user", "default", "delete",
            "desc", "distinct", "do", "else", "end", "except", "false", "fetch", "for", "foreign", "from", "grant",
            "group", "having", "id", "in", "index", "insert", "intersect", "into", "is", "is_sample", "join", "key",
            "like", "limit", "not", "null", "offset", "on", "only", "or", "order", "primary", "references", "select",
            "session_user", "set", "some", "table", "then", "to", "true", "union", "unique", "update", "user",
            "using", "values", "when", "where", "window", "with"}
TIME_TYPES = {"datetime", "date"}
_PERSONAL = re.compile(r"(^|_)(name|email|phone|address)($|_)")


@lru_cache(maxsize=1)
def load() -> dict[str, dict]:
    """Recipes by id, read once."""
    data = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["patterns"]}


def recipes_for(feature_id: str, business_type: str | None) -> list[str]:
    """Recipes that can serve a brief feature, best first: a recipe whose business words match comes first."""
    words = (business_type or "").lower()
    found = [p for p in load().values() if feature_id in p["features"]]
    return [p["id"] for p in sorted(found, key=lambda p: not any(w in words for w in p.get("business_words", [])))]


# ---------------------------------------------------------------- expansion
def _matches(when: dict | None, values: dict[str, str]) -> bool:
    for switch, wanted in (when or {}).items():
        allowed = wanted if isinstance(wanted, list) else [wanted]
        if values.get(switch) not in allowed:
            return False
    return True


def _number(recipe: dict, switch: str, value: str) -> Any:
    option = next((o for o in _switch(recipe, switch)["options"] if o["value"] == value), {})
    return option.get("number", value)


def _switch(recipe: dict, switch_id: str) -> dict:
    return next(s for s in recipe["switches"] if s["id"] == switch_id)


def _fill(value: Any, recipe: dict, values: dict[str, str]) -> Any:
    """'$switch' -> that switch's number; recurse into lists and dicts."""
    if isinstance(value, str) and value.startswith("$"):
        return _number(recipe, value[1:], values[value[1:]])
    if isinstance(value, list):
        return [_fill(v, recipe, values) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, recipe, values) for k, v in value.items()}
    return value


def resolve_switches(recipe: dict, chosen: dict[str, str], locked: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Owner's locked answers first, then the model's choices, then defaults. Returns (values, problems)."""
    values, problems = {}, []
    for s in recipe["switches"]:
        allowed = {o["value"] for o in s["options"]}
        owner = locked.get(f"{recipe['id']}.{s['id']}")
        model = chosen.get(s["id"])
        if owner in allowed:
            values[s["id"]] = owner
        elif model is not None and model not in allowed:
            problems.append(f"switch '{recipe['id']}.{s['id']}' has no option '{model}'")
            values[s["id"]] = s["default"]
        else:
            values[s["id"]] = model if model is not None else s["default"]
    problems += [f"recipe '{recipe['id']}' has no switch '{k}'" for k in chosen if k not in values]
    return values, problems


def _locked_by(when: dict | None, recipe_id: str, locked: dict[str, str]) -> bool:
    """Locked only when every answer it depends on came from the owner (one "Let FORGE decide" leaves it editable)."""
    return bool(when) and all(f"{recipe_id}.{s}" in locked for s in when)


def personal_name(name: str, ftype: str) -> bool:
    """A field that likely holds a person's details when visitors send it (a product's "name" is not)."""
    return ftype in ("email", "phone") or bool(_PERSONAL.search(name))


def expand(instances: list[dict], locked: dict[str, str] | None = None) -> tuple[list[DataEntity], list[str]]:
    """
    Recipes + switch values -> record types. An instance is {"pattern", "switches", "names", "labels", "feature_ids"}:
    `names` renames record types ("staff" -> "stylists") everywhere they are used, `labels` sets what the owner sees.
    Returns (entities, problems); problems are for the plan checks and fix rounds.
    """
    locked = locked or {}
    entities: dict[str, DataEntity] = {}
    problems: list[str] = []
    for inst in instances:
        recipe = load().get(inst.get("pattern", ""))
        if not recipe:
            problems.append(f"no recipe '{inst.get('pattern')}'")
            continue
        values, found = resolve_switches(recipe, inst.get("switches") or {}, locked)
        problems += found
        names = {k: v for k, v in (inst.get("names") or {}).items() if v}
        rename = lambda n: names.get(n, n)          # noqa: E731
        made: dict[str, DataEntity] = {}
        for spec in recipe["entities"]:
            if not _matches(spec.get("when"), values):
                continue
            fields = []
            for f in spec["fields"]:
                if not _matches(f.get("when"), values):
                    continue
                data = {k: v for k, v in f.items() if k != "when"}
                data = _fill(data, recipe, values)
                if data.get("default") is not None:
                    data["default"] = str(data["default"])
                if data.get("reference"):
                    data["reference"] = rename(data["reference"])
                data["personal"] = data.get("personal", False) or (spec["role"] == "submission"
                                                                    and personal_name(data["name"], data["type"]))
                data["locked"] = _locked_by(f.get("when"), recipe["id"], locked)
                fields.append(DataField(**data))
            name = rename(spec["name"])
            made[name] = DataEntity(
                name=name, label=(inst.get("labels") or {}).get(spec["name"]) or spec["label"], role=spec["role"],
                pattern=recipe["id"], purpose=spec.get("purpose", ""), fields=fields,
                feature_ids=list(inst.get("feature_ids") or []),
                links=list(dict.fromkeys(f.reference for f in fields if f.reference)),
                sample_rows=3)
        for r in recipe["rules"]:
            target = made.get(rename(r["entity"]))
            if not target or not _matches(r.get("when"), values):
                continue
            params = _fill(r["params"], recipe, values)
            for key in ("hours", "days_off"):              # params that name record types
                if isinstance(params.get(key), str):
                    params[key] = rename(params[key])
            target.rules.append(DataRule(rule_id="", kind=r["kind"], params=params,
                                         locked=_locked_by(r.get("when"), recipe["id"], locked)))
        for name, e in made.items():
            if name in entities:
                old = entities[name]
                if e.pattern == "catalogue" or old.pattern == "catalogue":   # the other recipe's own list serves it
                    if old.pattern == "catalogue":
                        entities[name] = e
                    continue
                problems.append(f"two recipes both make '{name}'; rename one")
                continue
            entities[name] = e
    out = list(entities.values())
    finish(out)
    return out, problems


def finish(entities: list[DataEntity]) -> None:
    """Code-owned details: rule ids, rule sentences, links. Run after any change (expansion, edits, patches)."""
    by_name = {e.name: e for e in entities}
    for e in entities:
        e.links = list(dict.fromkeys([*(f.reference for f in e.fields if f.reference), *e.links]))
        seen: dict[str, int] = {}
        for r in e.rules:
            seen[r.kind] = seen.get(r.kind, 0) + 1
            r.rule_id = f"{e.name}.{r.kind}" + (f".{seen[r.kind]}" if seen[r.kind] > 1 else "")
            r.label = describe(e, r, by_name)


def prompt_view(recipe_id: str, locked: dict[str, str]) -> dict:
    """What call 2 is told about a recipe: its switches (owner answers marked) and what it makes right now."""
    recipe = load()[recipe_id]
    values, _ = resolve_switches(recipe, {}, locked)
    entities, _ = expand([{"pattern": recipe_id}], locked)
    return {
        "pattern": recipe_id, "label": recipe["label"],
        "switches": [{"switch": s["id"], "question": s["question"], "options": [o["value"] for o in s["options"]],
                      "default": s["default"], **({"owner": values[s["id"]]}
                                                  if f"{recipe_id}.{s['id']}" in locked else {})}
                     for s in recipe["switches"]],
        "makes": [{"name": e.name, "role": e.role, "fields": [f"{f.name}:{f.type}" for f in e.fields],
                   "rules": [r.label for r in e.rules]} for e in entities],
    }


def build(design, locked: dict[str, str]) -> tuple[list[DataEntity], list[dict], list[str]]:
    """Call 2's choices -> (record types, the recipes with their final switch values, problems). `design` is a
    planning DataDesign: recipes expanded by code, extra fields added, custom record types converted."""
    instances, recipes = [], []
    for r in design.recipes:
        recipe = load().get(r.pattern)
        inst = {"pattern": r.pattern, "switches": {s.switch: s.value for s in r.switches},
                "names": {x.entity: x.name for x in r.renames if x.name},
                "labels": {x.entity: x.label for x in r.renames if x.label}, "feature_ids": list(r.feature_ids)}
        instances.append(inst)
        if recipe:
            recipes.append({**inst, "switches": resolve_switches(recipe, inst["switches"], locked)[0]})
    entities, problems = expand(instances, locked)
    by_name = {e.name: e for e in entities}
    for x in design.extra_fields:
        e = by_name.get(x.entity)
        if not e:
            problems.append(f"extra field '{x.field.name}' is for '{x.entity}', which no recipe makes")
        elif any(f.name == x.field.name for f in e.fields):
            problems.append(f"'{x.entity}' already has a field '{x.field.name}'")
        else:
            f = x.field.to_field()
            f.personal = f.personal or (e.role == "submission" and personal_name(f.name, f.type))
            e.fields.append(f)
    for c in design.entities:
        if c.name in by_name:
            problems.append(f"custom record type '{c.name}' has the same name as one a recipe makes")
            continue
        e = c.to_entity()
        for f in e.fields:
            f.personal = f.personal or (e.role == "submission" and personal_name(f.name, f.type))
        by_name[e.name] = e
        entities.append(e)
    finish(entities)
    return entities, recipes, problems


_STOP = {"the", "a", "an", "their", "your", "our", "his", "her", "its", "of", "for", "and", "or", "to", "with", "s"}


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower().replace("'s", " ")) if w not in _STOP]


def detail_covered(detail: str, entities: list[DataEntity]) -> bool:
    """A visitor detail ("pet's breed") is held when one field, read with its record type, has all its words:
    "breed" on appointments, or "name" on pets. Plural record type names count ("pets" holds "pet")."""
    wanted = _words(detail)
    if not wanted:
        return True
    for e in entities:
        for f in e.fields:
            text = " ".join(_words(f"{e.name} {e.label} {f.name} {f.label}"))
            if all(any(t.startswith(w) or w.startswith(t) for t in text.split()) for w in wanted):
                return True
    return False


# ---------------------------------------------------------------- plain-English rule sentences
def _field(e: DataEntity | None, name: str) -> DataField | None:
    return next((x for x in e.fields if x.name == name), None) if e else None


def _q(e: DataEntity | None, name: str) -> str:
    """A field as the owner sees it, in quotes: "Date and time"."""
    f = _field(e, name)
    return f'"{f.label if f and f.label else name.replace("_", " ")}"'


def _ref_label(e: DataEntity, field: str, by_name: dict[str, DataEntity]) -> str:
    f = _field(e, field)
    target = by_name.get(f.reference or "") if f else None
    return one((target.label if target and target.label else (f.label if f and f.label else field)).lower())


def one(label: str) -> str:
    """A plural label read as one item: "class times" -> "class time", "stylists" -> "stylist"."""
    if label.startswith("items "):                            # "items for rent" -> "item for rent"
        return "item " + label[len("items "):]
    if label.endswith("ies"):
        return label[:-3] + "y"
    return label[:-1] if label.endswith("s") and not label.endswith("ss") else label


def _hours(h: Any) -> str:
    h = float(h)
    if h >= 24 and h % 24 == 0:
        days = int(h // 24)
        return f"{days} day" + ("s" if days > 1 else "")
    return f"{h:g} hour" + ("s" if h != 1 else "")


def _start(e: DataEntity, p: dict, by_name: dict[str, DataEntity]) -> str:
    if p.get("via"):
        parent = by_name.get((_field(e, p["via"]) or DataField(name="x", type="text")).reference or "")
        return f"The {_ref_label(e, p['via'], by_name)}'s {_q(parent, p['start'])}"
    return _q(e, p["start"])


def describe(e: DataEntity, r: DataRule, by_name: dict[str, DataEntity]) -> str:
    """The sentence the owner reads on the review screen; code-made, never by a model."""
    p, what, k = r.params, (e.label or e.name).lower(), r.kind
    if k == "unique_together":
        return f"Only one {one(what)} per {' and '.join(_q(e, f) for f in p.get('fields', []))}"
    if k == "no_overlap":
        if p.get("resource"):
            return f"No two {what} for the same {_ref_label(e, p['resource'], by_name)} at overlapping times"
        return f"No two {what} at overlapping times"
    if k == "capacity":
        extra = "extra bookings go on the waitlist" if p.get("overflow") == "waitlist" else "extra bookings are refused"
        if p.get("parent"):
            parent = by_name.get((_field(e, p["parent"]) or DataField(name="x", type="text")).reference or "")
            counting = f", counting {_q(e, p['sum'])}" if p.get("sum") else ""
            return (f"Each {_ref_label(e, p['parent'], by_name)} takes at most its {_q(parent, p['parent_capacity'])}"
                    f"{counting}; {extra}")
        count = _q(e, p["sum"]) if p.get("sum") else "bookings"
        at = " and ".join(_q(e, f) for f in p.get("group_by", []))
        return f"At most {p.get('max')} in total of {count} at the same {at}; {extra}"
    if k == "within_hours":
        who = f" of the chosen {_ref_label(e, p['resource'], by_name)}" if p.get("resource") else ""
        return f"Only during the working hours{who}, and not on days off"
    if k == "lead_time":
        if not p.get("hours"):
            return f"{_start(e, p, by_name)} can't be in the past"
        return f"{_start(e, p, by_name)} must be at least {_hours(p['hours'])} ahead"
    if k == "max_advance":
        return f"{_start(e, p, by_name)} can be at most {int(p['days'])} days ahead"
    if k == "status_flow":
        moves = "; ".join(f"{a} → {', '.join(b)}" for a, b in p.get("moves", {}).items())
        return f"{_q(e, p['field'])} can only move: {moves}"
    if k == "range":
        return f"{_q(e, p['field'])} from {p.get('min'):g} to {p.get('max'):g}"
    if k == "required_if":
        must = "must be yes" if p.get("equals") is True else "is needed"
        return f"{_q(e, p['field'])} {must} when {_q(e, p['when_field'])} is {p['when_value']}"
    if k == "end_from_duration":
        parent = by_name.get((_field(e, p["via"]) or DataField(name="x", type="text")).reference or "")
        return (f"{_q(e, p['end'])} is worked out from the chosen {_ref_label(e, p['via'], by_name)}'s "
                f"{_q(parent, p.get('duration', 'duration'))}")
    if k == "date_order":
        days = p.get("min_days")
        tail = (f", by at least {int(days)} day" + ("s" if int(days) > 1 else "")) if days and int(days) > 0 else ""
        return f"{_q(e, p['end'])} must be after {_q(e, p['start'])}{tail}"
    return k


# ---------------------------------------------------------------- what code can compile (planning checks 20-23, 26)
def problems_in(entities: list[DataEntity]) -> list[str]:
    """Everything the SQL compiler relies on. Empty = safe to compile."""
    out: list[str] = []
    by_name = {e.name: e for e in entities}
    for e in entities:
        if not NAME.match(e.name) or e.name in RESERVED:
            out.append(f"26: record type name '{e.name}' is not allowed")
        names = [f.name for f in e.fields]
        if len(names) != len(set(names)):
            out.append(f"26: '{e.name}' has two fields with the same name")
        fields = {f.name: f for f in e.fields}
        for f in e.fields:
            if not NAME.match(f.name) or f.name in RESERVED:
                out.append(f"26: field name '{e.name}.{f.name}' is not allowed")
            if f.type == "reference" or f.reference:
                if f.type != "reference" or f.reference not in by_name:
                    out.append(f"20: '{e.name}.{f.name}' links to '{f.reference}', which is not defined")
            if f.type == "choice" and not (2 <= len(f.options) <= 20):
                out.append(f"23: choice field '{e.name}.{f.name}' needs 2 to 20 options")
            if f.type == "choice" and f.default is not None and f.default not in f.options:
                out.append(f"23: '{e.name}.{f.name}' default '{f.default}' is not one of its options")
        for r in e.rules:
            out += [f"22: rule '{r.rule_id or r.kind}' on '{e.name}': {m}" for m in _rule_problems(e, r, fields, by_name)]
    out += _loops(entities)
    return out


def _rule_problems(e: DataEntity, r: DataRule, fields: dict[str, DataField],
                   by_name: dict[str, DataEntity]) -> list[str]:
    p, out = r.params, []

    def need(key: str, types: set[str] | None = None, optional: bool = False, on: DataEntity | None = None):
        name = p.get(key)
        where = on or e
        pool = {f.name: f for f in where.fields}
        if name is None:
            if not optional:
                out.append(f"needs '{key}'")
            return None
        if name not in pool:
            out.append(f"'{key}' names '{name}', which '{where.name}' does not have")
            return None
        if types and pool[name].type not in types:
            out.append(f"'{key}' field '{name}' must be one of {sorted(types)}")
        return pool[name]

    def parent_of(key: str) -> DataEntity | None:
        f = need(key, {"reference"})
        return by_name.get(f.reference or "") if f else None

    k = r.kind
    if k == "unique_together":
        if not p.get("fields") or any(x not in fields for x in p["fields"]):
            out.append("'fields' must name fields of the record type")
    elif k == "no_overlap":
        need("resource", {"reference", "text", "choice"}, optional=True)
        s, t = need("start", TIME_TYPES), need("end", TIME_TYPES)
        if s and t and s.type != t.type:
            out.append("start and end must have the same type")
    elif k == "capacity":
        if p.get("overflow") not in ("refuse", "waitlist"):
            out.append("'overflow' must be refuse or waitlist")
        if p.get("sum"):
            need("sum", {"number"})
        if p.get("parent"):
            parent = parent_of("parent")
            if parent:
                need("parent_capacity", {"number"}, on=parent)
        elif not p.get("group_by") or any(x not in fields for x in p["group_by"]) or not _positive(p.get("max")):
            out.append("needs 'parent' and 'parent_capacity', or 'group_by' fields and a positive 'max'")
        if p.get("overflow") == "waitlist" and "Waitlist" not in (fields.get("status").options if fields.get("status") else []):
            out.append("a waitlist needs a status option 'Waitlist'")
    elif k == "within_hours":
        need("start", {"datetime"}), need("end", {"datetime"})
        need("resource", {"reference"}, optional=True)
        hours, off = by_name.get(p.get("hours", "")), by_name.get(p.get("days_off", ""))
        if not hours or not {"day", "opens", "closes"} <= {f.name for f in hours.fields}:
            out.append("'hours' must name a record type with day, opens and closes")
        if p.get("days_off") and (not off or "date" not in {f.name for f in off.fields}):
            out.append("'days_off' must name a record type with a date")
    elif k in ("lead_time", "max_advance"):
        number = p.get("hours" if k == "lead_time" else "days")
        if not isinstance(number, (int, float)) or number < 0:
            out.append("needs a number of hours or days, 0 or more")
        if p.get("via"):
            parent = parent_of("via")
            if parent:
                need("start", TIME_TYPES, on=parent)
        else:
            need("start", TIME_TYPES)
    elif k == "status_flow":
        f = need("field", {"choice"})
        moves = p.get("moves") or {}
        if f and (not moves or any(a not in f.options or any(b not in f.options for b in bs) for a, bs in moves.items())):
            out.append("'moves' must use the status options")
    elif k == "range":
        need("field", {"number", "money", "duration"})
        if not (isinstance(p.get("min"), (int, float)) and isinstance(p.get("max"), (int, float)) and p["min"] <= p["max"]):
            out.append("needs numbers 'min' <= 'max'")
    elif k == "required_if":
        need("field")
        w = need("when_field", {"choice", "boolean", "text"})
        if w is not None and w.type == "choice" and p.get("when_value") not in w.options:
            out.append(f"'when_value' must be one of {w.options}")
    elif k == "end_from_duration":
        s, t = need("start", {"datetime"}), need("end", {"datetime"})
        parent = parent_of("via")
        if parent:
            need("duration", {"duration"}, on=parent)
    elif k == "date_order":
        s, t = need("start", TIME_TYPES | {"time"}), need("end", TIME_TYPES | {"time"})
        if s and t and s.type != t.type:
            out.append("start and end must have the same type")
        if p.get("min_days") is not None and not isinstance(p["min_days"], (int, float)):
            out.append("'min_days' must be a number")
    return out


def _positive(x: Any) -> bool:
    return isinstance(x, (int, float)) and x > 0


def _loops(entities: list[DataEntity]) -> list[str]:
    """Required links must not form a loop, or no first row could ever be saved (check 21)."""
    needs = {e.name: {f.reference for f in e.fields if f.reference and f.required and not f.multiple} for e in entities}
    out, state = [], {}

    def visit(n: str, path: list[str]) -> None:
        state[n] = 1
        for m in needs.get(n, ()):
            if state.get(m) == 1:
                out.append(f"21: required links form a loop: {' -> '.join(path + [m])}")
            elif m in needs and not state.get(m):
                visit(m, path + [m])
        state[n] = 2

    for n in needs:
        if not state.get(n):
            visit(n, [n])
    return out
