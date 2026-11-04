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


def content_key(need: dict[str, Any]) -> str:
    """Where the owner's answer is stored. Lists without one catalogue key are named after the input, so two
    components that list the same things ("services") share one form field."""
    return need.get("content_key") or snake(need["name"])


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
        for need in needs_of(s, specs):
            if need["kind"] not in OWNER_KINDS:
                continue
            key = content_key(need)
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
