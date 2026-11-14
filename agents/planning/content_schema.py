# D:\FYP\FORGE-1\agents\planning\content_schema.py
"""
The business details form, derived by code from the Needs List (D-201) of the chosen components and the needs
the Planning Agent wrote for each custom part. It asks only for what the planned sections really use.
"""
import json
import re
from functools import lru_cache
from typing import Any

from agents.catalogue import COMPONENTS_DIR
from agents.state import ContentField, CustomComponentSpec, Need, PlannedComponent

NEEDS_FILE = COMPONENTS_DIR / "component_needs.json"
OWNER_KINDS = ("fact", "list", "image")
# Generic list names mean different things in different components (testimonials, FAQ and menu all have "items"),
# so they get one form field per component. Specific names ("services") stay shared across sections (KI-02).
GENERIC_LISTS = {"items", "categories", "features", "stats"}
_TYPE_FOR_KEY = {"phone": "phone", "whatsapp": "phone", "email": "email", "logo": "image", "photos": "image",
                 "map_embed_url": "url", "video_url": "url", "about_text": "long_text", "hours": "long_text"}


@lru_cache(maxsize=1)
def load_needs() -> dict[str, Any]:
    return json.loads(NEEDS_FILE.read_text(encoding="utf-8"))


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def needs_of(section: PlannedComponent, specs: dict[str, CustomComponentSpec]) -> list[dict[str, Any]]:
    """Every need of one section, as plain dicts in the Needs List format."""
    if section.custom_spec_id:
        spec = specs.get(section.custom_spec_id)
        return [n.model_dump() for n in spec.needs] if spec else []
    entry = load_needs().get(section.component_id or "")
    return entry["needs"] if entry else []


def content_key(need: dict[str, Any], owner: str = "") -> str:
    """Where the owner's answer is stored. Lists without one catalogue key are named after the input, so two
    components that list the same things ("services") share one form field; generic names are per component."""
    if need.get("content_key"):
        return need["content_key"]
    name = snake(need["name"])
    return f"{owner.replace('-', '_')}_{name}" if owner and name in GENERIC_LISTS else name


def section_keys(section: PlannedComponent, specs: dict[str, CustomComponentSpec]) -> list[tuple[dict[str, Any], str]]:
    """(need, form key) for every owner input of one section. Two inputs of one section never share a key
    (the before and after images both default to "photos")."""
    out, used = [], set()
    for need in needs_of(section, specs):
        if need["kind"] not in OWNER_KINDS:
            continue
        key = content_key(need, section.component_id or section.custom_spec_id or "")
        if key in used:
            key = f"{key}_{snake(need['name'])}"
        used.add(key)
        out.append((need, key))
    return out


def _field_type(need: dict[str, Any], key: str) -> str:
    if need["kind"] == "image":
        return "image"
    if need.get("type") in ContentField.model_fields["type"].annotation.__args__:
        return need["type"]
    return _TYPE_FOR_KEY.get(key, "text")


def _item_fields(need: dict[str, Any]) -> list[Need]:
    out = []
    for f in need.get("item_fields") or []:
        if f["kind"] == "code":
            continue                                       # ids and keys are made by code
        kind = f["kind"] if f["kind"] in ("fact", "image", "setting") else "fact"
        ftype = "boolean" if f.get("type") == "boolean" else "image" if kind == "image" else \
            f["type"] if f.get("type") in Need.model_fields["type"].annotation.__args__ else "text"
        out.append(Need(name=f["name"], kind=kind, type=ftype, required=f.get("required", True)))
    return out


def derive_content_schema(sections: list[PlannedComponent],
                          specs: dict[str, CustomComponentSpec]) -> list[ContentField]:
    fields: dict[str, ContentField] = {}
    for s in sections:
        for need, key in section_keys(s, specs):
            f = fields.get(key)
            if f is None:
                f = fields[key] = ContentField(
                    key=key, label=need.get("label") or key.replace("_", " ").capitalize(), kind=need["kind"],
                    type=_field_type(need, key), required=False)
            f.required = f.required or need.get("required", True)
            if s.section_id not in f.needed_by:
                f.needed_by.append(s.section_id)
            known = {i.name for i in f.item_fields}
            f.item_fields += [i for i in _item_fields(need) if i.name not in known]
    return list(fields.values())


# ---------------------------------------------------------------- sample content (D-225)
# A clearly marked sample for every field, until the owner fills the business details form. Never a real-looking
# fact (no invented prices, awards or addresses that could be mistaken for the owner's): obvious placeholders only.
_SAMPLE_BY_TYPE = {
    "text": "Sample {label}", "long_text": "Sample text: {business} details go here. Replace it with your own words.",
    "number": 1, "money": "Rs. 0", "date": "2026-01-01", "time": "10:00", "datetime": "2026-01-01T10:00",
    "email": "hello@example.com", "phone": "0300 0000000", "url": "", "boolean": False, "choice": "",
    "image": "/sample-image.svg",
}
SAMPLE_LIST_LENGTH = 3


def _sample(field_type: str, label: str, business: str):
    value = _SAMPLE_BY_TYPE.get(field_type, "Sample {label}")
    return value.format(label=label.lower(), business=business) if isinstance(value, str) else value


def sample_content(fields: list[ContentField], business_type: str | None) -> dict[str, Any]:
    """{content key: sample value}. The site shows a "sample content" banner while these are in use."""
    business = (business_type or "business").strip()
    out: dict[str, Any] = {}
    for f in fields:
        if f.key == "business_name":
            out[f.key] = f"Your {business.title()}"
        elif f.kind == "list":
            out[f.key] = [{i.name: _sample(i.type, f"{i.name.replace('_', ' ')} {n}", business) for i in f.item_fields}
                          for n in range(1, SAMPLE_LIST_LENGTH + 1)]
        else:
            out[f.key] = _sample("image" if f.kind == "image" else f.type, f.label, business)
    return out
