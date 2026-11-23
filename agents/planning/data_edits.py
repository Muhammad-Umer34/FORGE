# D:\FYP\FORGE-1\agents\planning\data_edits.py
"""
The owner's edits on "What your site will keep" (D-244): add or remove a field, make one required, turn a rule on or
off, change a rule's number, undo. Code only, no model call, and they do not use the one plain-English change.

Edits are kept as a list and replayed on the record types the planner made (`base`), so undo is "replay all but the
last" and a later plain-English change can re-apply them to the new plan. An edit that would break the data model is
refused with a plain message.
"""
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel

from agents.planning import data_patterns
from agents.state import DataEntity, DataField

# What the owner picks from, in their words -> the field type code uses.
SIMPLE_TYPES = {"Short text": "text", "Long text": "long_text", "Number": "number", "Price": "money", "Date": "date",
                "Time": "time", "Date and time": "datetime", "Email": "email", "Phone": "phone", "Web link": "url",
                "Yes / No": "boolean", "Choice from a list": "choice"}
TYPE_WORDS = {v: k for k, v in SIMPLE_TYPES.items()} | {"image": "Photo", "duration": "Length of time",
                                                         "reference": "Link to another list"}
# Numbers an owner may change, per rule kind: (setting, unit, min, max).
NUMBERS = {"lead_time": ("hours", "hours", 0, 720), "max_advance": ("days", "days", 1, 365),
           "date_order": ("min_days", "days", 0, 365), "capacity": ("max", "in total", 1, 10000)}
FIXED_RULES = {"end_from_duration"}                     # works out a value; turning it off would leave it empty


class DataEdit(BaseModel):
    op: Literal["add_field", "remove_field", "set_required", "toggle_rule", "set_number", "undo"]
    entity: Optional[str] = None
    field: Optional[str] = None                         # field name (remove, set_required)
    label: Optional[str] = None                         # new field's label (add)
    type: Optional[str] = None                          # one of SIMPLE_TYPES' keys (add)
    options: list[str] = []                             # for "Choice from a list"
    required: Optional[bool] = None
    rule_id: Optional[str] = None
    enabled: Optional[bool] = None
    value: Optional[float] = None


class EditRefused(ValueError):
    """Shown to the owner as the plan screen's notice."""


def _slug(label: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40] or "field"
    return name if name[0].isalpha() else f"f_{name}"[:40]


def _entity(entities: list[DataEntity], name: str | None) -> DataEntity:
    e = next((x for x in entities if x.name == name), None)
    if not e:
        raise EditRefused("That list is not part of this plan any more.")
    return e


def _used_by_rules(e: DataEntity, field: str) -> bool:
    def mentions(v: Any) -> bool:
        return v == field or (isinstance(v, list) and field in v)
    return any(mentions(v) for r in e.rules for v in r.params.values())


def apply_one(entities: list[DataEntity], edit: DataEdit, limits) -> None:
    """Apply one edit in place, or raise EditRefused."""
    e = _entity(entities, edit.entity)
    if edit.op == "add_field":
        if e.role == "setting":
            raise EditRefused(f"{e.label or e.name} is filled in by FORGE; fields cannot be added to it.")
        label = " ".join((edit.label or "").split())[:60]
        kind = SIMPLE_TYPES.get(edit.type or "")
        if not label or not kind:
            raise EditRefused("Give the new field a name and pick what kind of answer it takes.")
        name = _slug(label)
        if name in data_patterns.RESERVED:
            name = f"{name}_value"
        if any(f.name == name for f in e.fields):
            raise EditRefused(f'{e.label or e.name} already has a field called "{label}".')
        if len(e.fields) >= limits.max_fields_per_entity:
            raise EditRefused(f"{e.label or e.name} already has {limits.max_fields_per_entity} fields, the most a form can have.")
        options = list(dict.fromkeys(" ".join(o.split())[:60] for o in edit.options if o.strip()))
        if kind == "choice" and not 2 <= len(options) <= 20:
            raise EditRefused("A choice needs between 2 and 20 answers to pick from.")
        e.fields.append(DataField(name=name, label=label, type=kind, required=bool(edit.required),
                                  options=options if kind == "choice" else [],
                                  personal=e.role == "submission" and data_patterns.personal_name(name, kind)))
    elif edit.op in ("remove_field", "set_required"):
        f = next((x for x in e.fields if x.name == edit.field), None)
        if not f:
            raise EditRefused("That field is not part of this plan any more.")
        if f.locked:
            raise EditRefused(f'"{f.label or f.name}" follows one of your answers, so it stays.')
        if e.role == "setting":
            raise EditRefused(f"{e.label or e.name} is filled in by FORGE; its fields stay as they are.")
        if f.type == "reference" or f.name == "status" or _used_by_rules(e, f.name):
            raise EditRefused(f'"{f.label or f.name}" is needed by a rule or a link, so it stays.')
        if edit.op == "remove_field":
            if f.required:
                raise EditRefused(f'"{f.label or f.name}" is required. Make it optional first, then remove it.')
            e.fields.remove(f)
        else:
            f.required = bool(edit.required)
    elif edit.op in ("toggle_rule", "set_number"):
        r = next((x for x in e.rules if x.rule_id == edit.rule_id), None)
        if not r:
            raise EditRefused("That rule is not part of this plan any more.")
        if r.locked:
            raise EditRefused("This rule follows one of your answers. Start over to answer differently.")
        if edit.op == "toggle_rule":
            if r.kind in FIXED_RULES:
                raise EditRefused("FORGE needs this rule to work out a value; it cannot be turned off.")
            r.enabled = bool(edit.enabled)
        else:
            setting = NUMBERS.get(r.kind)
            key = setting[0] if setting else None
            if not setting or key not in r.params or edit.value is None:
                raise EditRefused("This rule has no number to change.")
            if not setting[2] <= edit.value <= setting[3]:
                raise EditRefused(f"Pick a number from {setting[2]} to {setting[3]}.")
            r.params[key] = int(edit.value) if float(edit.value).is_integer() else float(edit.value)
    data_patterns.finish(entities)
    problems = data_patterns.problems_in(entities)
    if problems:
        raise EditRefused("That change would break how the data fits together, so it was not made.")


def replay(base: list[dict], edits: list[dict], limits) -> tuple[list[DataEntity], list[dict]]:
    """Base record types + the kept edits -> (record types, edits that still apply)."""
    entities = [DataEntity.model_validate(e) for e in base]
    kept = []
    for raw in edits:
        try:
            apply_one(entities, DataEdit.model_validate(raw), limits)
            kept.append(raw)
        except EditRefused:
            entities = replay(base, kept, limits)[0]           # an edit that no longer fits is dropped
    return entities, kept


def view(entities: list[DataEntity]) -> list[dict]:
    """What the review screen shows, in the owner's words."""
    by_name = {e.name: e for e in entities}
    out = []
    for e in entities:
        fields = []
        for f in e.fields:
            fixed = (f.locked or e.role == "setting" or f.type == "reference" or f.name == "status"
                     or _used_by_rules(e, f.name))
            fields.append({
                "name": f.name, "label": f.label or f.name.replace("_", " ").capitalize(),
                "kind": (by_name[f.reference].label if f.reference in by_name else TYPE_WORDS.get(f.type, f.type))
                if f.type == "reference" else TYPE_WORDS.get(f.type, f.type),
                "options": f.options, "required": f.required, "personal": f.personal,
                "removable": not fixed and not f.required, "can_toggle_required": not fixed,
                "why_fixed": ("follows one of your answers" if f.locked else "filled in by FORGE" if e.role == "setting"
                              else "needed by a rule or a link") if fixed else "",
            })
        rules = []
        for r in e.rules:
            setting = NUMBERS.get(r.kind)
            number = None
            if setting and setting[0] in r.params:
                number = {"value": r.params[setting[0]], "unit": setting[1], "min": setting[2], "max": setting[3]}
            rules.append({"rule_id": r.rule_id, "label": r.label, "enabled": r.enabled, "locked": r.locked,
                          "can_toggle": not r.locked and r.kind not in FIXED_RULES,
                          "number": number if not r.locked else None})
        out.append({"name": e.name, "label": e.label or e.name, "role": e.role, "fields": fields, "rules": rules,
                    "can_add_field": e.role != "setting"})
    return out
