"""The Integration Agent's join and checks (D-252): the parts of four real plans fit, and every planted fault between
them is caught. No database, no model: every side is made by the agents' own code."""
import json

import pytest

from agents.backend_generator.agent import contract_json, form_specs, schemas_ts
from agents.database_generator.compile import compile_schema
from agents.frontend_generator.compiler import compile_site
from agents.frontend_generator.custom_writer import Part, accept
from agents.integration import JoinError, join, run_checks
from agents.integration.checks import page_forms, schema_fields
from test_backend_agent import bakery_plan, salon_plan
from test_planning import (CHOSEN, DataDesign, RecipeChoice, SiteDesign, _live_brief, _sections, built_plan, page)


def _one_form_plan(business, recipe, feature, component):
    brief = _live_brief(business, [(feature, "must")], ["home", feature], [feature])
    site = SiteDesign(direction=CHOSEN, pages=[page("home", "/", "Home"), page(feature, f"/{feature}", "Join")],
                      sections=_sections((feature, feature, component)))
    return built_plan(brief, site, DataDesign(recipes=[RecipeChoice(pattern=recipe, feature_ids=[feature])], routes=[]))[1]


PLANS = {"salon": salon_plan, "bakery": bakery_plan,
         "yoga": lambda: _one_form_plan("yoga studio", "classes", "booking", "booking-form"),
         "jobs": lambda: _one_form_plan("hiring company", "applications", "contact-form", "contact-form")}


def parts(plan):
    specs = form_specs(plan)
    backend = {"lib/forms.json": json.dumps(specs, indent=2, ensure_ascii=False), "lib/schemas.ts": schemas_ts(specs),
               "api/contract.json": contract_json(plan, specs)} if specs else {}
    return {"database": compile_schema(plan.data_entities, "site_abc123").files(), "backend": backend,
            "frontend": compile_site(plan, "business", "req_integration")}


def site(plan, change=None, model_paths=frozenset()):
    p = parts(plan)
    if change:
        change(p)
    files, _ = join(p, model_paths)
    return run_checks(files, plan, model_paths)


def failed(checks, cid):
    return [c.message for c in checks if c.id == cid and not c.ok]


@pytest.mark.parametrize("name", PLANS)
def test_the_parts_of_a_real_plan_fit(name):
    plan = PLANS[name]()
    p = parts(plan)
    files, manifest = join(p)
    assert page_forms(files), f"{name}: no DataForm placed"
    checks = run_checks(files, plan)
    assert [c.message for c in checks if not c.ok] == []
    assert {c.id for c in checks} >= {"I1", "I2", "I3", "I4", "I7", "I8", "I10", "I12"}
    assert {"database", "backend", "frontend", "integration"} == set(manifest["agents"])
    assert next(f for f in manifest["files"] if f["path"] == "lib/schemas.ts")["agent"] == "backend"


def test_the_join_refuses_two_parts_that_disagree_and_keeps_no_secrets():
    p = parts(salon_plan())
    p["frontend"]["lib/schemas.ts"] += "// changed"
    with pytest.raises(JoinError, match="lib/schemas.ts differently"):
        join(p)
    files, _ = join(parts(salon_plan()))
    assert "FORGE_SITE_KEY=\n" in files[".env.example"] and "fsk_" not in files[".env.example"]


def _edit_json(path, fn):
    def change(p):
        owner = next(a for a, own in p.items() if path in own)
        data = json.loads(p[owner][path])
        fn(data)
        p[owner][path] = json.dumps(data)
    return change


def _table(data, name):
    return next(t for t in data["tables"] if t["name"] == name)


def test_a_form_posting_to_a_missing_route_is_caught():
    checks = site(salon_plan(), _edit_json("api/contract.json", lambda d: d["routes"].__setitem__(
        slice(None), [r for r in d["routes"] if r["method"] != "POST"])))
    assert any("POST /api/data/appointments" in m for m in failed(checks, "I2"))


def test_a_public_list_of_bookings_is_caught():
    def add(d):
        d["routes"].append({"route_id": "GET /api/data/appointments", "method": "GET", "path": "/api/data/appointments",
                            "entity": "appointments", "request_fields": [], "used_by": []})
    assert failed(site(salon_plan(), _edit_json("api/contract.json", add)), "I3")


def test_a_form_field_the_table_does_not_keep_is_caught():
    def drop(d):
        t = _table(d, "appointments")
        t["columns"] = [c for c in t["columns"] if c["name"] != "phone"]
    assert any("'phone'" in m for m in failed(site(salon_plan(), _edit_json("db/schema.json", drop)), "I4"))


def test_a_required_column_the_form_leaves_out_is_caught():
    def add(d):
        _table(d, "appointments")["columns"].append({"name": "pet_name", "type": "text", "required": True,
                                                    "default": None, "visitor": True, "multiple": False})
    assert any("'pet_name'" in m for m in failed(site(salon_plan(), _edit_json("db/schema.json", add)), "I4"))


def test_a_choice_from_a_private_list_is_caught():
    assert failed(site(salon_plan(), _edit_json("db/schema.json",
                                                lambda d: _table(d, "stylists").update(role="submission"))), "I5")


def test_order_items_that_do_not_link_to_the_order_are_caught():
    def unlink(d):
        items = next(t for t in d["tables"] if t["name"] != "orders" and any(c.get("reference") == "orders"
                                                                               for c in t["columns"]))
        for c in items["columns"]:
            if c.get("reference") == "orders":
                c["reference"] = None
    assert failed(site(bakery_plan(), _edit_json("db/schema.json", unlink)), "I6")


def test_a_personal_form_without_consent_is_caught():
    def no_consent(d):
        for spec in d.values():
            spec["consent"] = False
    def both(p):                                  # the page carries the same spec, so I1 holds
        _edit_json("lib/forms.json", no_consent)(p)
        for path, text in p["frontend"].items():
            p["frontend"][path] = text.replace('"consent": true', '"consent": false')
    checks = site(salon_plan(), both)
    assert failed(checks, "I7") and not failed(checks, "I1")


def test_a_page_form_without_its_spec_and_a_stale_zod_schema_are_caught():
    def stale(p):
        p["backend"]["lib/forms.json"] = p["backend"]["lib/forms.json"].replace('"Your name"', '"Name"')
        p["backend"]["lib/schemas.ts"] = p["backend"]["lib/schemas.ts"].replace("    phone:", "    telephone:")
        p["frontend"]["lib/schemas.ts"] = p["backend"]["lib/schemas.ts"]
    checks = site(salon_plan(), stale)
    assert failed(checks, "I1") and failed(checks, "I8")
    assert schema_fields(parts(salon_plan())["backend"]["lib/schemas.ts"])["appointments"][:2] == ["client_name", "phone"]


def test_an_ai_part_that_calls_the_api_is_caught_and_refused_when_written():
    path = "components/custom/gallery/Gallery.tsx"
    def add(p):
        p["frontend"][path] = 'export function Gallery() { fetch("/api/photos"); return null }'
    assert failed(site(salon_plan(), add, {path}), "I9")
    part = Part(section_id="home.gallery", kind="custom", name="Gallery", file=path, export_name="Gallery",
                props_code="")
    files, why = accept(part, {path: 'export function Gallery() { const k = process.env.FORGE_SITE_KEY; return null }'})
    assert files is None and "process.env" in why


def test_a_link_to_a_missing_page_and_a_missing_page_file_are_caught():
    def break_links(p):
        path = next(f for f, text in p["frontend"].items() if '"href": "/services"' in text)
        p["frontend"][path] = p["frontend"][path].replace('"href": "/services"', '"href": "/pricing"', 1)
        del p["frontend"]["app/booking/page.tsx"]
    checks = site(salon_plan(), break_links)
    msgs = failed(checks, "I10")
    assert any("/pricing" in m for m in msgs) and any("/booking has no file" in m for m in msgs)
