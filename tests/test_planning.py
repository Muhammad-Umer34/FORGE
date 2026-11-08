"""
The Planning Agent subgraph (plan v2, D-204, D-205) with a fake model: the salon example end to end through the
plan-approval pause, the skipped data call, every plan check, fix rounds, the text pitch rules and plan changes.
"""
import json
from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import Command

from agents.catalogue import load_catalogue
from agents.gateway import CallUsage
from agents.planning import assemble, build_planning_graph, checks, nodes, texts
from agents.planning.schemas import (
    CustomSpecOut, DataDesign, NeedOut, PlanFix, SectionOut, SiteDesign, SiteTexts, TextOut,
)
from agents.retrieval.ranker import rank_and_retrieve_components
from agents.state import (
    AcceptanceTest, ApiRoute, BriefFeature, ClarifiedBrief, DashboardView, DataEntity, DataField, FormRule, GraphState,
    Limits, PlannedPage, RequestInfo, TextSlot, UnsupportedItem, initial_state,
)

THEME = {"theme_id": "t-1", "params": {"personality": "elegant"}, "tokens": {"light": {"primary": "#b0522b"}}}


# ---------------------------------------------------------------- fixtures
def feature(fid, priority="must", tier="catalogued", name=None):
    return BriefFeature(id=fid, name=name or fid.replace("-", " "), priority=priority, source="user_stated", tier=tier)


def acceptance(tid, ref):
    return AcceptanceTest(test_id=tid, requirement_ref=ref, kind="happy_path", ears="WHEN x THE SYSTEM SHALL y",
                          given="a visitor", when="they open the site", then=f"they see {ref}",
                          check="element_present", description=ref, expected_result=ref)


def salon_brief() -> ClarifiedBrief:
    return ClarifiedBrief(
        status="ready", frozen_at=datetime.now(timezone.utc), baseline="booking", business_type="hair salon",
        goal="Let clients book haircuts and see prices", audience="local clients",
        features=[feature("booking"), feature("services-price-list"), feature("gallery", "should"),
                  feature("whatsapp-chat"), feature("location-map", "should"),
                  feature("custom-loyalty-stamp-card", tier="custom", name="loyalty stamp card"),
                  feature("online-payments", tier="unsupported")],
        pages=[{"name": "home", "sections": ["services-price-list"]}, {"name": "booking", "sections": ["booking"]}],
        theme=THEME,
        unsupported=[UnsupportedItem(asked="card payments online", capability_id="online-payments", group="feature",
                                     reason="FORGE cannot take payments.", alternative_text="Pay at the salon.")],
        test_cases=[acceptance("T01", "booking"), acceptance("T02", "services-price-list"),
                    acceptance("T03", "whatsapp-chat"), acceptance("T04", "custom-loyalty-stamp-card")],
    )


def info_brief() -> ClarifiedBrief:
    return ClarifiedBrief(
        status="ready", frozen_at=datetime.now(timezone.utc), baseline="brochure", business_type="accounting firm",
        goal="Show the firm's accounting services", features=[feature("about-story"), feature("services-overview"),
                                                             feature("contact-info")],
        pages=[{"name": "home", "sections": ["services-overview"]}, {"name": "about", "sections": ["about-story"]}],
        theme=THEME, test_cases=[acceptance("T01", "services-overview")])


def page(pid, route, title, in_menu=True):
    return PlannedPage(page_id=pid, route=route, title=title, in_menu=in_menu)


def salon_site(drop=()) -> SiteDesign:
    sections = [SectionOut(page_id="home", feature_id="services-price-list", component_id="services-price-list"),
                SectionOut(page_id="home", feature_id="custom-loyalty-stamp-card",
                           custom_spec_id="custom-loyalty-stamp-card"),
                SectionOut(page_id="booking", feature_id="booking", component_id="booking-form"),
                SectionOut(page_id="gallery", feature_id="gallery", component_id="gallery-carousel"),
                SectionOut(page_id="contact", feature_id="location-map", component_id="location-map")]
    return SiteDesign(
        pages=[page("home", "/", "Home"), page("booking", "/booking", "Book"), page("gallery", "/gallery", "Gallery"),
               page("contact", "/contact", "Contact")],
        sections=[s for s in sections if s.feature_id not in drop], footer_links=["home", "contact"],
        custom_specs=[CustomSpecOut(spec_id="custom-loyalty-stamp-card", feature_id="custom-loyalty-stamp-card",
                                    name="Loyalty stamp card", page_id="home", purpose="Shows how loyalty visits work.",
                                    needs=[NeedOut(name="stamps_for_reward", kind="fact", type="number",
                                                   label="Stamps needed for a free visit"),
                                           NeedOut(name="title", kind="copy", max_length=70)])])


def salon_data() -> DataDesign:
    person = [DataField(name="full_name", type="text", personal=True), DataField(name="email", type="email", personal=True),
              DataField(name="phone", type="phone", personal=True)]
    return DataDesign(
        entities=[DataEntity(name="booking_requests", fields=person + [DataField(name="service", type="text"),
                                                                        DataField(name="date", type="date"),
                                                                        DataField(name="time", type="time")]),
                  DataEntity(name="time_slots", fields=[DataField(name="date", type="date"),
                                                        DataField(name="time", type="time")])],
        routes=[ApiRoute(route_id="POST /api/bookings", method="POST", path="/api/bookings", entity="booking_requests",
                         request_fields=["full_name", "email", "phone", "service", "date", "time"],
                         used_by=["booking.booking"]),
                ApiRoute(route_id="GET /api/availability", method="GET", path="/api/availability", entity="time_slots",
                         used_by=["booking.booking"])],
        form_rules=[FormRule(section_id="booking.booking", route_id="POST /api/bookings",
                             required_fields=["full_name", "phone"], rules=["no two bookings for the same slot"])],
        dashboard_views=[DashboardView(entity="booking_requests", title="Bookings",
                                       columns=["Name", "Phone", "Service", "Date", "Time", "Status"],
                                       statuses=["New", "Confirmed", "Done"], default_status="New")])


def good_texts(user: str, heroes=("Welcome to our website", "Fresh haircuts, booked in a minute",
                                  "Your next haircut starts here")) -> SiteTexts:
    """Text for every slot in the prompt that passes the pitch rules: unique titles, verbs on buttons."""
    slots = json.loads(user.split("Text slots to write:\n")[1].split("\n\nProblems")[0])
    out = []
    for s in slots:
        if s["slot_id"] == assemble.HERO_HEADLINE:
            continue
        words = f"Salon {s['page']} {s['feature']}".replace("-", " ").lower()
        text = "Book a visit" if s["button"] else words.capitalize()
        out.append(TextOut(slot_id=s["slot_id"], text=text[:s["max_length"]]))
    return SiteTexts(hero_headlines=list(heroes), texts=out)


class FakeModel:
    """Answers each schema from a queue (first answer is reused when the queue runs dry); records every call."""

    def __init__(self, site=None, data=None, fixes=(), texts_fn=good_texts):
        self.answers = {SiteDesign: [site or salon_site()], DataDesign: [data or salon_data()], PlanFix: list(fixes)}
        self.texts_fn, self.calls = texts_fn, []

    def __call__(self, task, schema, system, user):
        self.calls.append((task, schema.__name__))
        if schema is SiteTexts:
            return self.texts_fn(user), CallUsage(calls=1)
        queue = self.answers[schema]
        return (queue.pop(0) if len(queue) > 1 else queue[0]), CallUsage(calls=1)


def _section(user: str, title: str, end: str):
    return json.loads(user.split(title + "\n")[1].split("\n\n" + end)[0])


def any_brief_planner(heroes: tuple[str, ...]) -> FakeModel:
    """A fake model that plans any brief: every feature on Home with its first found component, a custom part for
    each custom feature, and an entity and routes for every section that sends or shows data."""
    def site(user):
        brief = _section(user, "Brief:", "Placed by code")
        opts = _section(user, "Found components per feature (choose from these):", "Inputs")
        pages = [page("home", "/", "Home")] + [page(p["name"], f"/{p['name']}", p["name"].title())
                                               for p in brief["pages"] if p["name"] != "home"]
        return SiteDesign(
            pages=pages,
            sections=[SectionOut(page_id="home", feature_id=f, component_id=ids[0] if ids else None,
                                 custom_spec_id=None if ids else f) for f, ids in opts.items()],
            custom_specs=[CustomSpecOut(spec_id=f, feature_id=f, name=f, page_id="home", purpose="A custom part.",
                                        needs=[NeedOut(name="title", kind="copy", max_length=70)])
                          for f, ids in opts.items() if not ids])

    def data(user):
        out = DataDesign()
        for s in _section(user, "Sections that send or show data:", "Standard"):
            name = s["feature_id"].replace("-", "_") + "_records"
            fields = [DataField(name=f, type="text", personal=f in ("name", "fullName", "email", "phone"))
                      for f in s["sends"] or ["name"]]
            out.entities.append(DataEntity(name=name, fields=fields))
            if s["is_form"]:
                route = f"POST /api/{name}"
                out.routes.append(ApiRoute(route_id=route, method="POST", path=f"/api/{name}", entity=name,
                                           request_fields=s["sends"], used_by=[s["section_id"]]))
                out.form_rules.append(FormRule(section_id=s["section_id"], route_id=route))
            if s["shows_live"]:
                out.routes.append(ApiRoute(route_id=f"GET /api/{name}", method="GET", path=f"/api/{name}",
                                           entity=name, used_by=[s["section_id"]]))
            if any(f.personal for f in fields):
                out.dashboard_views.append(DashboardView(entity=name, title=name, columns=["Name"]))
        return out

    fake = FakeModel(texts_fn=lambda user: good_texts(user, heroes))
    fake.answers = {SiteDesign: [], DataDesign: [], PlanFix: []}
    builders = {SiteDesign: site, DataDesign: data}
    plain = fake.__call__

    def call(task, schema, system, user):
        if schema in builders:
            fake.calls.append((task, schema.__name__))
            return builders[schema](user), CallUsage(calls=1)
        return plain(task, schema, system, user)
    return call


def run_graph(brief, fake, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake)
    builder = StateGraph(GraphState)
    builder.add_node("planning", build_planning_graph())
    builder.add_edge(START, "planning")
    graph = builder.compile(checkpointer=InMemorySaver())
    state = initial_state(RequestInfo(request_id="r", user_id="u", project_id="p", prompt="x",
                                      created_at=datetime.now(timezone.utc)))
    state.update(brief=brief, retrieval=rank_and_retrieve_components(brief))
    config = {"configurable": {"thread_id": "t"}}
    result = graph.invoke(state, config)
    return graph, config, result


def inner(graph, config) -> dict:
    """The planning subgraph's own state while it is paused (the parent sees it only when the subgraph ends)."""
    return graph.get_state(config, subgraphs=True).tasks[0].state.values


def built_plan(brief=None, site=None, data=None):
    brief = brief or salon_brief()
    plan = assemble.build_plan(brief, rank_and_retrieve_components(brief), assemble.tidy(site or salon_site()),
                               data if data is not None else salon_data(), load_catalogue())
    for t in plan.texts:
        t.text = "x"
    return brief, plan


# ---------------------------------------------------------------- end to end
def test_salon_plan_end_to_end_through_approval(monkeypatch):
    fake = FakeModel()
    graph, config, result = run_graph(salon_brief(), fake, monkeypatch)
    view = result["__interrupt__"][0].value
    assert view["type"] == "plan_approval" and [p["route"] for p in view["pages"]][:2] == ["/", "/booking"]
    assert view["pages"][0]["sections"][0] == "Hero Banner" and view["pages"][1]["sections"][0] == "Inner Page Header Banner"
    assert view["hero_headline"] == "Fresh haircuts, booked in a minute"            # generic first one rejected
    assert "Welcome to our website" in view["hero_alternatives"]
    assert view["stored"][0]["title"] == "Bookings" and view["not_built"][0]["asked"] == "card payments online"

    plan = inner(graph, config)["plan"]
    keys = {f.key for f in plan.content_schema}
    assert {"stamps_for_reward", "services", "whatsapp", "business_name"} <= keys      # custom part asks too
    assert next(f for f in plan.content_schema if f.key == "services").needed_by == ["home.services-price-list", "booking.booking"]   # one list, two sections
    assert plan.form_rules[0].consent_required and plan.form_rules[0].success_slot == "booking.booking.successMessage"
    assert {t.test_id: t.targets for t in plan.test_map}["T01"] == ["booking.booking", "POST /api/bookings",
                                                                    "GET /api/availability"]
    assert plan.custom_specs[0].needs[0].type == "number" and plan.theme == THEME
    assert [c.section_id for c in plan.components if c.page == "all"] == ["all.navbar", "all.footer", "all.whatsapp-chat"]

    done = graph.invoke(Command(resume={"decision": "approve"}), config)
    assert done["plan"].status == "approved" and done["plan"].approved_at
    assert done["planning"].status == "done" and done["planning"].calls_used == 3
    assert [c for c, _ in fake.calls] == ["planning", "planning", "planning"]


def test_a_site_that_stores_nothing_skips_the_data_call_and_the_backend(monkeypatch):
    site = SiteDesign(pages=[page("home", "/", "Home"), page("about", "/about", "About")],
                      sections=[SectionOut(page_id="home", feature_id="services-overview", component_id="features-grid"),
                                SectionOut(page_id="about", feature_id="about-story", component_id="about-us"),
                                SectionOut(page_id="home", feature_id="contact-info", component_id="contact-info-block")])
    fake = FakeModel(site=site, texts_fn=lambda user: good_texts(user, ("Clear accounting for growing businesses",)))
    graph, config, result = run_graph(info_brief(), fake, monkeypatch)
    assert "__interrupt__" in result
    plan = inner(graph, config)["plan"]
    assert DataDesign.__name__ not in [s for _, s in fake.calls]
    assert not plan.data_entities and not plan.api_routes
    assert {t.task_id: t.skip for t in plan.execution_order} == {"database": True, "backend": True, "frontend": False,
                                                                 "content_form": False, "integration": False}


# ---------------------------------------------------------------- fix rounds
def test_a_missing_must_feature_goes_back_to_the_model_once(monkeypatch):
    fake = FakeModel(site=salon_site(drop=("booking",)), fixes=[PlanFix(site=salon_site(), data=salon_data())])
    graph, config, result = run_graph(salon_brief(), fake, monkeypatch)
    p = inner(graph, config)["planning"]
    assert "__interrupt__" in result and p.fix_rounds_used == 1
    assert ("planning_fix", "PlanFix") in fake.calls


def test_planning_stops_after_two_failed_fix_rounds(monkeypatch):
    broken = salon_site(drop=("booking",))
    fake = FakeModel(site=broken, fixes=[PlanFix(site=broken, data=salon_data())])
    graph, config, result = run_graph(salon_brief(), fake, monkeypatch)
    p = result["planning"]
    assert p.status == "failed" and p.fix_rounds_used == 2 and "__interrupt__" not in result
    assert p.failure.category == "system" and "must feature 'booking'" in p.failure.detail


# ---------------------------------------------------------------- checks
def _issues(brief, plan, limits=None):
    return checks.run_checks(plan, brief, rank_and_retrieve_components(brief), load_catalogue(), limits or Limits())


def test_a_good_plan_passes_every_check():
    brief, plan = built_plan()
    assert _issues(brief, plan) == []


def _no_home(p): p.pages[0].route = "/start"
def _unreachable(p): p.pages[2].in_menu = False; p.footer_links = ["home"]
def _hero_not_first(p): p.pages[0].section_ids.reverse()
def _two_footers(p): p.components.append(p.components[1].model_copy(update={"section_id": "all.footer2"}))
def _wrong_component(p): next(c for c in p.components if c.feature_id == "booking").component_id = "contact-form"
def _payments_part(p): p.custom_specs[0].purpose = "Takes online payments for visits."
def _no_form_field(p): p.content_schema = [f for f in p.content_schema if f.key != "stamps_for_reward"]
def _form_without_route(p): p.form_rules = []
def _unknown_entity(p): p.api_routes[0].entity = "orders"
def _no_consent(p): p.form_rules[0].consent_required = False
def _too_many_routes(p): p.api_routes += [p.api_routes[1].model_copy(update={"route_id": f"GET /api/x{i}", "path": f"/api/x{i}"}) for i in range(9)]
def _test_unlinked(p): p.test_map[0].targets = []
def _theme_changed(p): p.theme = {"theme_id": "other"}
def _real_phone(p): p.pages[3].purpose = "Call 0300 1234567"
def _loop(p): p.execution_order[0].depends_on = ["integration"]


@pytest.mark.parametrize("break_it, number", [
    (_no_home, "1:"), (_unreachable, "1:"), (_hero_not_first, "2:"), (_two_footers, "2:"), (_wrong_component, "4:"),
    (_payments_part, "5:"), (_no_form_field, "6:"), (_form_without_route, "8:"), (_unknown_entity, "9:"),
    (_no_consent, "11:"), (_too_many_routes, "12:"), (_test_unlinked, "13:"), (_theme_changed, "14:"),
    (_real_phone, "15:"), (_loop, "16:"),
])
def test_each_check_catches_its_fault(break_it, number):
    brief, plan = built_plan()
    break_it(plan)
    assert any(i.startswith(number) for i in _issues(brief, plan)), _issues(brief, plan)


def test_code_puts_home_at_the_root_first_and_numbers_the_menu():
    site = salon_site()
    site.pages[0].route = "/home"                      # as a live run returned, twice, after being told
    site.pages.reverse()
    tidy = assemble.tidy(site)
    assert [(p.page_id, p.route, p.menu_order) for p in tidy.pages] == [
        ("home", "/", 0), ("contact", "/contact", 1), ("gallery", "/gallery", 2), ("booking", "/booking", 3)]
    brief, plan = built_plan(site=site)
    assert _issues(brief, plan) == []


def _live_brief(business, features, pages, tests):
    return ClarifiedBrief(status="ready", frozen_at=datetime.now(timezone.utc), business_type=business, goal="x",
                          features=[feature(f, p) for f, p in features], pages=[{"name": n, "sections": []} for n in pages],
                          theme=THEME, test_cases=[acceptance(f"T0{i}", ref) for i, ref in enumerate(tests, 1)])


def _sections(*rows):
    return [SectionOut(page_id=pg, feature_id=f, component_id=c) for pg, f, c in rows]


def _person():
    return [DataField(name="customer_name", type="text", personal=True), DataField(name="phone", type="phone", personal=True),
            DataField(name="email", type="email", personal=True)]


def test_the_live_bakery_design_passes_without_a_fix_round():
    """req_ec38c1bbb3d4: the POST route had no used_by, no form rule or dashboard view, and an unused GET route."""
    brief = _live_brief("bakery", [("menu-catalog", "must"), ("order-request", "must"), ("location-map", "must"),
                                   ("about-story", "should"), ("contact-info", "should")],
                        ["home", "about", "contact", "menu", "order"],
                        ["menu-catalog", "order-request", "location-map", "order-request", "about-story", "contact-info"])
    site = SiteDesign(pages=[page("home", "/", "Home"), page("menu", "/menu", "Menu"), page("order", "/order", "Order"),
                             page("about", "/about", "About"), page("contact", "/contact", "Contact")],
                      sections=_sections(("menu", "menu-catalog", "menu-catalog-grid"),
                                         ("order", "order-request", "order-request-form"), ("about", "about-story", "about-us"),
                                         ("contact", "location-map", "location-map"),
                                         ("contact", "contact-info", "contact-info-block")))
    data = DataDesign(
        entities=[DataEntity(name="cake_items", fields=[DataField(name="name", type="text")]),
                  DataEntity(name="order_requests", feature_ids=["order-request"],
                             fields=_person() + [DataField(name="items", type="long_text")])],
        routes=[ApiRoute(route_id="GET /api/menu", method="GET", path="/api/menu", entity="cake_items",
                         used_by=["menu.menu-catalog"]),
                ApiRoute(route_id="POST /api/orders", method="POST", path="/api/orders", entity="order_requests",
                         request_fields=["customer_name", "phone", "email", "items"]),
                ApiRoute(route_id="GET /api/orders", method="GET", path="/api/orders", entity="order_requests")])
    _, plan = built_plan(brief, site, data)
    assert _issues(brief, plan) == []
    assert [(r.section_id, r.route_id, r.consent_required) for r in plan.form_rules] == [
        ("order.order-request", "POST /api/orders", True)]
    assert "GET /api/orders" not in {r.route_id for r in plan.api_routes}
    assert [v.entity for v in plan.dashboard_views] == ["order_requests"]


def test_the_live_salon_design_passes_without_a_fix_round():
    """req_c89c88eead73: used_by held feature ids, the POST route had none, and a route used no stored type."""
    brief = _live_brief("hair salon", [("booking", "must"), ("services-price-list", "must"),
                                       ("services-overview", "should"), ("contact-info", "should")],
                        ["home", "booking", "contact", "services"],
                        ["booking", "services-price-list", "booking", "services-overview", "contact-info"])
    site = SiteDesign(pages=[page("home", "/", "Home"), page("services", "/services", "Services"),
                             page("booking", "/booking", "Book"), page("contact", "/contact", "Contact")],
                      sections=_sections(("home", "services-overview", "features-grid"),
                                         ("services", "services-price-list", "services-price-list"),
                                         ("booking", "booking", "booking-form"), ("contact", "contact-info", "contact-info-block")))
    data = DataDesign(
        entities=[DataEntity(name="services", feature_ids=["services-price-list"], fields=[DataField(name="name", type="text")]),
                  DataEntity(name="booking_requests", feature_ids=["booking"],
                             fields=_person() + [DataField(name="date", type="date"), DataField(name="time", type="time")])],
        routes=[ApiRoute(route_id="GET /api/services", method="GET", path="/api/services", entity="services",
                         used_by=["services-price-list"]),
                ApiRoute(route_id="POST /api/bookings", method="POST", path="/api/bookings", entity="booking_requests",
                         request_fields=["customer_name", "phone", "email", "date", "time"]),
                ApiRoute(route_id="GET /api/availability", method="GET", path="/api/availability",
                         entity="booking_requests", used_by=["booking.booking"]),
                ApiRoute(route_id="GET /api/contact", method="GET", path="/api/contact", used_by=["contact-info"])])
    _, plan = built_plan(brief, site, data)
    assert _issues(brief, plan) == []
    routes = {r.route_id: r.used_by for r in plan.api_routes}
    assert routes["GET /api/services"] == ["services.services-price-list"] and "GET /api/contact" not in routes
    assert routes["POST /api/bookings"] == ["booking.booking"]


def test_a_fix_that_makes_the_plan_worse_is_thrown_away(monkeypatch):
    worse = PlanFix(site=salon_site(drop=("booking", "services-price-list", "gallery")), data=salon_data())
    fake = FakeModel(site=salon_site(drop=("booking",)), fixes=[worse, PlanFix(site=salon_site(), data=salon_data())])
    graph, config, result = run_graph(salon_brief(), fake, monkeypatch)
    p = inner(graph, config)["planning"]
    assert "__interrupt__" in result and p.fix_rounds_used == 2 and p.before_fix is None


def test_a_must_feature_without_a_section_and_data_on_an_info_site_are_caught():
    brief, plan = built_plan(site=salon_site(drop=("booking",)))
    assert any(i.startswith("3:") for i in _issues(brief, plan))
    brief = info_brief()
    site = SiteDesign(pages=[page("home", "/", "Home")],
                      sections=[SectionOut(page_id="home", feature_id="services-overview", component_id="features-grid")])
    data = salon_data()
    data.routes[1].used_by = ["home.services-overview"]    # a real section, but one that sends and shows nothing
    _, plan = built_plan(brief, site, data)
    assert any(i.startswith("10:") for i in _issues(brief, plan))


# ---------------------------------------------------------------- text rules
def _slot(prop="title", max_length=70):
    return TextSlot(slot_id=f"home.x.{prop}", section_id="home.x", prop=prop, max_length=max_length)


@pytest.mark.parametrize("prop, text, problem", [
    ("title", "Welcome to our website", "generic phrase"),
    ("title", "20 years of experience in styling", "invented claim"),
    ("title", "Cuts from 500 rupees", "a number or price"),
    ("title", "The best salon in Lahore", "invented claim"),
    ("primaryCtaText", "Our prices", "start with a verb"),
    ("title", "Visit {owner_name} today", "not allowed"),
    ("headline", "Fresh cuts and colour for every single kind of hair", "more than 8 words"),
])
def test_text_that_breaks_a_pitch_rule_is_rejected(prop, text, problem):
    rules = texts.TextRules(relevance={"hair", "salon"}, placeholders={"business_name"})
    assert any(problem in p for p in texts.check_text(_slot(prop), text, rules))


def test_good_text_passes_and_repeated_titles_and_an_off_topic_hero_are_caught():
    rules = texts.TextRules(relevance={"hair", "salon", "haircut"}, placeholders={"business_name"})
    assert texts.check_text(_slot("primaryCtaText", 28), "Book your haircut", rules) == []
    assert texts.check_text(_slot(), "Haircuts at {business_name}", rules) == []
    slots = [TextSlot(slot_id="home.hero.headline", section_id="home.hero", prop="headline", max_length=70,
                      text="Feel good today"),
             TextSlot(slot_id="a.x.title", section_id="a.x", prop="title", max_length=70, text="Our work"),
             TextSlot(slot_id="b.x.title", section_id="b.x", prop="title", max_length=70, text="Our work")]
    problems = texts.check_all(slots, rules)
    assert "b.x.title" in problems and "does not say what this business offers" in problems["home.hero.headline"][0]


def test_the_hero_is_the_best_candidate_that_passes():
    rules = texts.TextRules(relevance={"hair", "salon"}, placeholders={"business_name"})
    slot = _slot("headline")
    chosen, rest = texts.pick_hero(["Welcome to our salon", "Feel good today", "Hair that suits your day"], slot, "",
                                   rules)
    assert chosen == "Hair that suits your day" and rest == ["Welcome to our salon", "Feel good today"]


def test_text_that_still_fails_after_the_rewrite_is_left_out_when_optional(monkeypatch):
    def bad_badges(user):
        out = good_texts(user)
        for t in out.texts:
            if t.slot_id.endswith("badgeText"):
                t.text = "Award winning"
        return out
    fake = FakeModel(texts_fn=bad_badges)
    graph, config, result = run_graph(salon_brief(), fake, monkeypatch)
    plan = inner(graph, config)["plan"]
    assert "__interrupt__" in result and inner(graph, config)["planning"].text_rewrites_used == 1
    assert all(t.text == "" for t in plan.texts if t.slot_id.endswith("badgeText"))


# ---------------------------------------------------------------- plan changes
def test_one_change_is_applied_and_then_no_more_are_allowed(monkeypatch):
    changed = salon_site()
    changed.sections[3].component_id = "image-gallery"
    fake = FakeModel(fixes=[PlanFix(site=changed, data=salon_data())])
    graph, config, _ = run_graph(salon_brief(), fake, monkeypatch)
    after = graph.invoke(Command(resume={"decision": "change", "change_text": "Use a grid gallery"}), config)
    view = after["__interrupt__"][0].value
    assert next(pg for pg in view["pages"] if pg["route"] == "/gallery")["sections"][1] == "Image Gallery"
    assert view["changes_left"] == 0
    again = graph.invoke(Command(resume={"decision": "change", "change_text": "Add a blog"}), config)
    assert "No more changes" in again["__interrupt__"][0].value["notice"]


def test_a_change_that_breaks_the_plan_is_undone(monkeypatch):
    fake = FakeModel(fixes=[PlanFix(site=salon_site(drop=("booking",)), data=salon_data())])
    graph, config, _ = run_graph(salon_brief(), fake, monkeypatch)
    before = inner(graph, config)["plan"]
    after = graph.invoke(Command(resume={"decision": "change", "change_text": "Remove booking"}), config)
    assert "could not be made" in after["__interrupt__"][0].value["notice"]
    assert inner(graph, config)["plan"] == before


def test_cancel_ends_planning_without_a_plan_approval(monkeypatch):
    graph, config, _ = run_graph(salon_brief(), FakeModel(), monkeypatch)
    done = graph.invoke(Command(resume={"decision": "cancel"}), config)
    assert done["planning"].status == "cancelled" and done["plan"].status == "draft"


def test_planning_stops_when_the_brief_is_not_confirmed(monkeypatch):
    brief = salon_brief()
    brief.status, brief.frozen_at = "draft", None
    fake = FakeModel()
    _, _, result = run_graph(brief, fake, monkeypatch)
    assert result["planning"].status == "failed" and fake.calls == []
