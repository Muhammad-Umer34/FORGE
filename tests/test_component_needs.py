"""
The Component Needs List (components/component_needs.json) must match the components' code, so the Planning
Agent never plans a component that would render empty. Rebuild it with components/build_component_needs.py.
"""
import json
import sys
from pathlib import Path

import pytest

COMPONENTS = Path(__file__).resolve().parents[1] / "components"
sys.path.insert(0, str(COMPONENTS))
import build_component_needs as builder  # noqa: E402

NEEDS = json.loads((COMPONENTS / "component_needs.json").read_text(encoding="utf-8"))
CATALOGUE = {e["component_id"]: e for e in json.loads((COMPONENTS / "components_catalog.json").read_text(encoding="utf-8"))}
KINDS = {"copy", "fact", "list", "image", "setting", "live", "code"}


def test_the_list_is_up_to_date_with_the_components_code():
    # A new or renamed Props input changes the rebuilt list, so this fails until the file is rebuilt and reviewed.
    assert builder.build() == NEEDS, "run: .venv\\Scripts\\python.exe components\\build_component_needs.py"


def test_every_component_file_and_catalogue_entry_is_described():
    files = {p.name for p in COMPONENTS.glob("*.tsx")}
    assert {c["file"] for c in NEEDS.values()} == files
    assert set(CATALOGUE) <= set(NEEDS)


@pytest.mark.parametrize("component_id", sorted(NEEDS))
def test_each_need_is_well_formed(component_id):
    for need in NEEDS[component_id]["needs"]:
        assert need["kind"] in KINDS, need
        if need["kind"] == "copy":
            assert 0 < need["max_length"] <= 400, need          # the text step needs a length limit
        if need["kind"] == "code":
            assert not need["required"], need                    # wiring is never asked of anyone
        for key in [need.get("content_key")] + need.get("content_keys", []):
            assert key is None or key in builder.CONTENT_KEYS, need


@pytest.mark.parametrize("component_id", sorted(CATALOGUE))
def test_every_catalogue_content_need_has_a_place(component_id):
    entry = NEEDS[component_id]
    covered = ({n.get("content_key") for n in entry["needs"]}
               | {k for n in entry["needs"] for k in n.get("content_keys", [])}
               | set(entry.get("content_used_elsewhere", {})))
    assert set(CATALOGUE[component_id]["contentNeeds"]) <= covered


def test_forms_record_what_they_send():
    booking = {n["name"]: n for n in NEEDS["booking-form"]["needs"]}
    sent = [f["name"] for f in booking["onSubmit"]["submit_fields"]]
    assert {"serviceName", "date", "time", "fullName", "phone"} <= set(sent)   # the data model starts from this
