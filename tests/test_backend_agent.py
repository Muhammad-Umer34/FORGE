"""The Backend Agent (D-247): form specs and zod schemas written from the plan, and the backend gate run through
FORGE's real data service on the site's own storage."""
import json
import uuid

import psycopg
import pytest

from agents import build_worker
from agents.backend_generator import agent as backend_agent
from agents.backend_generator.agent import form_specs, schemas_ts
from agents.database_generator import provision
from agents.file_store import MemoryFileStore
from agents.state import RunConfig
from backend.core.config import settings
from backend.services import site_data
from backend.services.site_data import Storage
from pg_support import requires_db
from test_planning import (CHOSEN, DataDesign, DataFieldOut, ExtraField, RecipeChoice, Rename, SiteDesign,
                           SwitchValue, _live_brief, _sections, built_plan, page)


def salon_plan():
    brief = _live_brief("hair salon", [("booking", "must"), ("services-price-list", "must")],
                        ["home", "booking", "services"], ["booking", "services-price-list"])
    site = SiteDesign(direction=CHOSEN, pages=[page("home", "/", "Home"), page("services", "/services", "Services"),
                                               page("booking", "/booking", "Book")],
                      sections=_sections(("services", "services-price-list", "services-price-list"),
                                         ("booking", "booking", "booking-form")))
    data = DataDesign(
        recipes=[RecipeChoice(pattern="appointments", feature_ids=["booking"],
                              switches=[SwitchValue(switch="choose_staff", value="yes")],
                              renames=[Rename(entity="staff", name="stylists", label="Stylists")])],
        extra_fields=[ExtraField(entity="appointments", field=DataFieldOut(
            name="hair_length", label="Hair length", type="choice", options=["Short", "Medium", "Long"], required=False))],
        routes=[])
    return built_plan(brief, site, data)[1]


def bakery_plan():
    brief = _live_brief("bakery", [("order-request", "must")], ["home", "order"], ["order-request"])
    site = SiteDesign(direction=CHOSEN, pages=[page("home", "/", "Home"), page("order", "/order", "Order")],
                      sections=_sections(("order", "order-request", "order-request-form")))
    data = DataDesign(recipes=[RecipeChoice(pattern="orders", feature_ids=["order-request"])], routes=[])
    return built_plan(brief, site, data)[1]


def test_a_booking_form_spec_has_every_field_the_plan_keeps():
    plan = salon_plan()
    (sid, spec), = form_specs(plan).items()
    assert sid == "booking.booking" and spec["table"] == "appointments" and spec["consent"] is True
    fields = {f["name"]: f for f in spec["fields"]}
    assert "end_at" not in fields and "status" not in fields                    # worked out by code
    assert fields["staff_id"]["list"] == {"table": "stylists", "label": "name"}
    assert fields["service_id"]["required"] and fields["hair_length"]["options"] == ["Short", "Medium", "Long"]
    assert spec["times"] == {"field": "start_at", "picks": ["staff_id", "service_id"]}
    assert plan.form_rules[0].route_id == "POST /api/data/appointments"          # the real path (D-247)


def test_an_order_form_has_its_items():
    (spec,) = form_specs(bakery_plan()).values()
    assert spec["table"] == "orders" and spec["items"]["table"] == "order_items"
    assert {f["name"] for f in spec["items"]["fields"]} == {"item_id", "quantity"}
    assert "times" not in spec


def test_zod_schemas_are_strict_and_use_the_owners_words():
    ts = schemas_ts(form_specs(salon_plan()))
    assert "appointments: z.object({" in ts and ".strict()" in ts
    assert 'hair_length: z.enum(["Short", "Medium", "Long"]' in ts and ").optional()," in ts
    assert "Please fill in 'Phone'." in ts and "Please choose a valid service." in ts
    assert "consent: z.literal(true" in ts
    order = schemas_ts(form_specs(bakery_plan()))
    assert "items: z.array(z.object({ item_id: z.uuid(" in order and ".min(1, { error: \"Please add at least one item.\" })" in order


@pytest.mark.skipif(not (build_worker.TEMPLATE / "node_modules" / "next").is_dir(), reason="site_template packages")
def test_generated_schemas_type_check_in_a_real_site():
    files = {"lib/schemas.ts": schemas_ts({**form_specs(salon_plan()), **{f"o.{k}": v for k, v in form_specs(bakery_plan()).items()}}),
             "app/page.tsx": "export default function Page() { return null }\n"}
    result = build_worker.build(files, build_id=f"test-schemas-{uuid.uuid4().hex[:6]}")
    typecheck = result.steps[0]
    assert typecheck.ok, "\n".join(f"{i.file}:{i.line} {i.message}" for i in typecheck.issues[:20]) or typecheck.output


def test_files_are_written_without_storage(monkeypatch):
    store = MemoryFileStore()
    monkeypatch.setattr(backend_agent, "active_store", lambda: store)
    lines = []
    out = backend_agent.run(salon_plan(), "req_b1", "test", RunConfig(), lines.append)
    assert {f.path for f in out.files} == {"lib/forms.json", "lib/schemas.ts", "api/contract.json"}
    assert json.loads(store.read("req_b1")["api/contract.json"])["forms"] == {"booking.booking": "appointments"}
    assert lines[0]["message"].startswith("Backend: 1 form")


@requires_db
@pytest.mark.parametrize("make", [salon_plan, bakery_plan])
def test_the_backend_gate_passes_on_real_storage(make):
    url = provision.plain_url(settings.TEST_DATABASE_URL)
    site_data.use_pool(None)
    site_data.pool(url)
    plan, project = make(), str(uuid.uuid4())
    made = provision.provision(plan.data_entities, url, project)
    try:
        storage = Storage(project, made["schema"], made["role"], made["contract"])
        from agents.backend_generator.gate import run_gate
        passed, total, failures = run_gate(storage, plan, form_specs(plan))
        assert failures == [] and passed == total >= 4
        with psycopg.connect(url) as conn:                                   # everything was rolled back
            left = conn.execute(f'SELECT count(*) FROM "{made["schema"]}"."{form_specs(plan) and next(iter(form_specs(plan).values()))["table"]}" '
                                "WHERE NOT is_sample").fetchone()[0]
        assert left == 0
    finally:
        provision.drop(url, project)
        site_data.pool().close()
        site_data.use_pool(None)


@pytest.mark.skipif(not (build_worker.TEMPLATE / "node_modules" / "next").is_dir(), reason="site_template packages")
def test_a_salon_with_data_form_builds_for_production():
    """D-248: the booking page draws DataForm from its spec; the whole site type-checks and builds."""
    from agents.frontend_generator import compile_site
    plan = salon_plan()
    files = compile_site(plan, "salon", "build")
    assert "<DataForm" in files["app/booking/page.tsx"]
    assert files["lib/schemas.ts"] == schemas_ts(form_specs(plan))          # written by the compiler too
    result = build_worker.build(files, build_id=f"test-dataform-{uuid.uuid4().hex[:6]}")
    failed = [s for s in result.steps if not s.ok]
    assert not failed, "\n".join(f"{i.file}:{i.line} {i.message}" for s in failed for i in s.issues[:20]) or failed[0].output[-2000:]


def test_a_section_the_booking_route_serves_gets_a_form_even_without_a_submit():
    """Live (journal #34): the planner put the slot picker, which has no submit, on the booking page; the booking
    route listed that section. It must still get DataForm, or visitors cannot book."""
    plan = salon_plan()
    plan.form_rules = []
    for c in plan.components:
        if c.section_id == "booking.booking":
            c.component_id = "appointment-slot-picker"
    (sid, spec), = form_specs(plan).items()
    assert sid == "booking.booking" and spec["table"] == "appointments" and spec["consent"] is True


def test_a_missing_field_gets_the_owners_words_not_zods():
    """Live: a booking without a phone got zod's 'expected string, received undefined'."""
    ts = schemas_ts(form_specs(salon_plan()))
    assert "phone: z.string({ error: \"Please fill in 'Phone'.\" })" in ts
