"""
The typed Build Plan (D-202): a full plan validates, each generator sees only its part, the planning slice is
in every new run, and plans survive a checkpoint round trip.
"""
from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import ValidationError

from agents.state import (
    STATE_VERSION, AGENT_READS, ApiRoute, BuildPlan, ContentField, CustomComponentSpec, DashboardView, DataEntity,
    DataField, FormRule, Need, NotBuilt, PlannedComponent, PlannedPage, PlanningState, PlanTestLink, RequestInfo,
    RunConfig, TextSlot, WorkTask, initial_state, msgpack_allowlist, plan_section, view_for,
)


def salon_plan() -> BuildPlan:
    """The salon example from plan v2, as the Planning Agent would produce it."""
    stamps = Need(name="stamps_for_reward", kind="fact", label="Stamps needed for a free visit", type="number")
    return BuildPlan(
        pages=[PlannedPage(page_id="home", route="/", title="Home", section_ids=["home.hero", "home.prices", "home.loyalty"]),
               PlannedPage(page_id="booking", route="/booking", title="Book a visit", menu_order=1,
                           section_ids=["booking.form"])],
        components=[
            PlannedComponent(section_id="all.navbar", page="all", role="layout", component_id="navbar"),
            PlannedComponent(section_id="home.hero", page="home", role="layout", component_id="hero-banner"),
            PlannedComponent(section_id="home.prices", page="home", order=1, feature_id="services-price-list",
                             component_id="services-price-list", satisfies=["T03"]),
            PlannedComponent(section_id="home.loyalty", page="home", order=2, role="custom", custom=True,
                             feature_id="custom-loyalty-stamp-card", custom_spec_id="custom-loyalty-stamp-card"),
            PlannedComponent(section_id="booking.form", page="booking", feature_id="booking",
                             component_id="booking-form", settings={}, satisfies=["T01", "T02"]),
        ],
        custom_specs=[CustomComponentSpec(spec_id="custom-loyalty-stamp-card", feature_id="custom-loyalty-stamp-card",
                                          name="Loyalty stamp card", page="home", purpose="Shows visits earned.",
                                          needs=[stamps, Need(name="title", kind="copy", max_length=70)])],
        theme={"theme_id": "t-1", "tokens": {"light": {"primary": "#b0522b"}}},
        content_schema=[
            ContentField(key="phone", label="Phone number", type="phone", needed_by=["booking.form"]),
            ContentField(key="services", label="Your services", kind="list", needed_by=["home.prices"],
                         item_fields=[Need(name="name", kind="fact"), Need(name="price", kind="fact", type="money")]),
            ContentField(key="stamps_for_reward", label=stamps.label, type="number", needed_by=["home.loyalty"]),
        ],
        texts=[TextSlot(slot_id="home.hero.headline", section_id="home.hero", prop="headline",
                        text="Look your best, every visit", max_length=70,
                        alternatives=["Your style, our care", "Book your best look today"])],
        data_entities=[DataEntity(name="booking_requests", feature_ids=["booking"], fields=[
            DataField(name="full_name", type="text", personal=True), DataField(name="phone", type="phone", personal=True),
            DataField(name="date", type="date"), DataField(name="time", type="time")])],
        api_routes=[ApiRoute(route_id="POST /api/bookings", method="POST", path="/api/bookings",
                             entity="booking_requests", request_fields=["full_name", "phone", "date", "time"],
                             used_by=["booking.form"], satisfies=["T01", "T02"])],
        form_rules=[FormRule(section_id="booking.form", route_id="POST /api/bookings", consent_required=True,
                             required_fields=["full_name", "phone"])],
        dashboard_views=[DashboardView(entity="booking_requests", title="Bookings",
                                       columns=["Name", "Phone", "Date", "Time", "Status"],
                                       statuses=["New", "Confirmed", "Done"], default_status="New")],
        execution_order=[WorkTask(task_id="database"), WorkTask(task_id="backend", depends_on=["database"]),
                         WorkTask(task_id="frontend"),
                         WorkTask(task_id="integration", depends_on=["frontend", "backend", "database"])],
        test_map=[PlanTestLink(test_id="T01", targets=["booking.form", "POST /api/bookings"])],
        not_built=[NotBuilt(asked="card payments online", reason="FORGE cannot process payments.")],
    )


def test_a_full_plan_validates_and_keeps_custom_needs():
    plan = salon_plan()
    spec = plan.custom_specs[0]
    assert spec.needs[0].kind == "fact" and spec.needs[0].type == "number"
    assert plan.content_schema[1].item_fields[1].type == "money"
    assert plan.version == 1 and plan.status == "draft"


@pytest.mark.parametrize("bad", [
    lambda: Need(name="x", kind="opinion"),                              # unknown kind
    lambda: DataField(name="x", type="blob"),                             # unknown field type
    lambda: WorkTask(task_id="publishing"),                               # not a build task
])
def test_unknown_values_are_refused(bad):
    with pytest.raises(ValidationError):
        bad()


def test_each_generator_sees_only_its_part_of_the_plan():
    plan = salon_plan()
    front = plan_section(plan, "frontend")
    assert {"components", "custom_specs", "theme", "texts", "api_routes"} <= set(front)
    assert "data_entities" not in front and "dashboard_views" not in front
    back = plan_section(plan, "backend")
    assert set(back) == {"data_entities", "api_routes", "form_rules", "dependencies"}
    assert set(plan_section(plan, "database")) == {"data_entities"}
    assert set(plan_section(plan, "content_form")) == {"content_schema"}
    assert view_for("content_form", {"plan": plan, "content": None})["plan"] == {"content_schema": front["content_schema"]}


def test_a_new_run_has_the_planning_slice_and_version_two():
    state = initial_state(RequestInfo(request_id="r", user_id="u", project_id="p", prompt="x",
                                      created_at=datetime.now(timezone.utc)))
    assert isinstance(state["planning"], PlanningState) and state["planning"].status == "idle"
    assert "planning" in AGENT_READS["planning"] and "brief" in AGENT_READS["planning"]
    assert STATE_VERSION == 2 and RunConfig().state_version == 2


def test_plans_survive_a_checkpoint_round_trip():
    serde = JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist())
    plan = salon_plan()
    restored = serde.loads_typed(serde.dumps_typed({"plan": plan, "planning": PlanningState(status="drafting")}))
    assert restored["plan"] == plan and restored["planning"].status == "drafting"
