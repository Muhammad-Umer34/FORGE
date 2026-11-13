# D:\FYP\FORGE-1\agents\planning\assemble.py
"""
Planning step 5 (plan v2 §5), code only: tidy what the model designed, merge it with the fixed parts and work
out everything that follows from it: sections in order, the business details form, the text slots, the data
contract with consent rules, the work plan, the test map and the not-built list.
"""
from agents.catalogue import Catalogue
from agents.planning import fixed
from agents.planning.content_schema import derive_content_schema, load_needs, needs_of
from agents.planning.schemas import DataDesign, SiteDesign
from agents.state import (
    Assumption, BuildPlan, ClarifiedBrief, CustomComponentSpec, DashboardView, FormRule, Need, NotBuilt,
    PlannedComponent, PlannedPage, PlanTestLink, RetrievalResult, TextSlot, WorkTask,
)

HERO_HEADLINE = "home.hero.headline"


def section_id(page_id: str, feature_id: str) -> str:
    return f"{page_id}.{feature_id}"


def tidy(site: SiteDesign) -> SiteDesign:
    """Code fixes first: Home is always at "/" and first, the menu is numbered in page order, drop sections on
    pages that do not exist and a feature repeated on one page, keep footer links to real pages (all pages when
    none are given), and put any page no one can reach into the footer."""
    site = site.model_copy(deep=True)
    for p in site.pages:
        p.page_id, p.route = p.page_id.strip().lower(), "/" + p.route.strip().strip("/").lower()
        if p.page_id == "home":
            p.route = "/"                     # the model sometimes writes "/home" and does not fix it when told
    for item in (*site.sections, *site.custom_specs):
        item.page_id = item.page_id.strip().lower()           # page ids are lower-cased, so references must be (KI-14)
    site.footer_links = [f.strip().lower() for f in site.footer_links]
    site.pages.sort(key=lambda p: p.page_id != "home")
    for order, p in enumerate(p for p in site.pages if p.in_menu):
        p.menu_order = order
    pages = {p.page_id for p in site.pages}
    seen, sections = set(), []
    for s in site.sections:
        key = (s.page_id, s.feature_id)
        if s.page_id in pages and key not in seen:
            seen.add(key)
            sections.append(s)
    site.sections = sections
    site.footer_links = [p for p in dict.fromkeys(site.footer_links) if p in pages] or [p.page_id for p in site.pages]
    site.footer_links += [p.page_id for p in site.pages if not p.in_menu and p.page_id not in site.footer_links]
    return site


def form_sections(plan: BuildPlan) -> list[str]:
    """Sections that send something to the site's backend: catalogue forms, and custom parts given a form rule."""
    specs = {s.spec_id: s for s in plan.custom_specs}
    out = [c.section_id for c in plan.components
           if any(n["name"] == "onSubmit" for n in needs_of(c, specs)) and not c.custom]
    custom = {c.section_id for c in plan.components if c.custom}
    return out + [r.section_id for r in plan.form_rules if r.section_id in custom and r.section_id not in out]


def live_sections(plan: BuildPlan) -> list[str]:
    specs = {s.spec_id: s for s in plan.custom_specs}
    return [c.section_id for c in plan.components if any(n["kind"] == "live" for n in needs_of(c, specs))]


def data_sections(plan: BuildPlan) -> list[dict]:
    """What call 2 is told about each section that sends or shows data."""
    specs = {s.spec_id: s for s in plan.custom_specs}
    out = []
    for c in plan.components:
        needs = needs_of(c, specs)
        sends = [f["name"] for n in needs for f in n.get("submit_fields") or []]
        live = [n["name"] for n in needs if n["kind"] == "live"]
        is_form = any(n["name"] == "onSubmit" for n in needs)
        if sends or live or is_form:
            out.append({"section_id": c.section_id, "feature_id": c.feature_id, "component_id": c.component_id,
                        "is_form": is_form, "sends": sends, "shows_live": live})
    return out


def _spec(spec, page_ids: set[str]) -> CustomComponentSpec:
    needs = [Need(**{**n.model_dump(exclude={"item_fields"}),
                     "item_fields": [Need(**f.model_dump()) for f in n.item_fields]}) for n in spec.needs]
    return CustomComponentSpec(spec_id=spec.spec_id, feature_id=spec.feature_id, name=spec.name,
                               page=spec.page_id if spec.page_id in page_ids else "home", purpose=spec.purpose,
                               behaviour=spec.behaviour, needs=needs, ui_notes=spec.ui_notes)


def _components(site: SiteDesign, brief: ClarifiedBrief, cat: Catalogue,
                specs: dict[str, CustomComponentSpec]) -> list[PlannedComponent]:
    out = [PlannedComponent(section_id=sid, page="all", role="layout", component_id=cid, feature_id=fid)
           for sid, cid, fid in fixed.site_wide(brief, cat)]
    limitations = {f.id: f.limitation for f in brief.features}
    for page in site.pages:
        first = (fixed.HERO if page.page_id == "home"
                 else (section_id(page.page_id, "header"), *fixed.PAGE_HEADER))
        out.append(PlannedComponent(section_id=first[0], page=page.page_id, role="layout",
                                    component_id=first[1], feature_id=first[2]))
        for order, s in enumerate((s for s in site.sections if s.page_id == page.page_id), start=1):
            custom = bool(s.custom_spec_id) and not s.component_id
            if custom and s.custom_spec_id in specs:
                specs[s.custom_spec_id].limitation = limitations.get(s.feature_id)
            out.append(PlannedComponent(
                section_id=section_id(page.page_id, s.feature_id), page=page.page_id, order=order,
                role="custom" if custom else "feature", feature_id=s.feature_id,
                component_id=None if custom else s.component_id, custom=custom,
                custom_spec_id=s.custom_spec_id if custom else None,
                settings={x.name: x.value for x in s.settings}, rationale=s.rationale))
    return out


def _together_pages(site: SiteDesign, pages: list[PlannedPage], comps: list[PlannedComponent]) -> None:
    """Blog posts: the post page goes with the blog list (D-203 note), outside the menu."""
    for fid, (_, extra, route) in fixed.TOGETHER.items():
        if any(c.feature_id == fid for c in comps) and not any(p.route == route for p in pages):
            pid = extra
            pages.append(PlannedPage(page_id=pid, route=route, title="Post", in_menu=False,
                                     purpose="One page per item, opened from the list"))
            comps.append(PlannedComponent(section_id=f"{pid}.{fid}", page=pid, role="feature", feature_id=fid,
                                          component_id=extra))


def _text_slots(comps: list[PlannedComponent], specs: dict[str, CustomComponentSpec],
                old: list[TextSlot]) -> list[TextSlot]:
    kept = {t.slot_id: t for t in old}
    slots = []
    for c in comps:
        for n in needs_of(c, specs):
            if n["kind"] == "copy":
                sid = f"{c.section_id}.{n['name']}"
                slot = TextSlot(slot_id=sid, section_id=c.section_id, prop=n["name"],
                                max_length=n.get("max_length") or 200)
                if sid in kept:
                    slot.text, slot.alternatives = kept[sid].text, kept[sid].alternatives
                slots.append(slot)
    return slots


def _work_plan(plan: BuildPlan) -> list[WorkTask]:
    no_db, no_api = not plan.data_entities, not plan.api_routes
    why = "the site stores nothing"
    return [
        WorkTask(task_id="database", owns=["database/"], skip=no_db, skip_reason=why if no_db else ""),
        WorkTask(task_id="backend", depends_on=["database"], owns=["backend/"], skip=no_api,
                 skip_reason=why if no_api else ""),
        WorkTask(task_id="frontend", owns=["frontend/"]),
        WorkTask(task_id="content_form", owns=["content/"]),
        WorkTask(task_id="integration", depends_on=["frontend", "backend", "database"], owns=["integration/"]),
    ]


def _test_map(brief: ClarifiedBrief, plan: BuildPlan) -> list[PlanTestLink]:
    links = []
    for t in brief.test_cases:
        sections = [c.section_id for c in plan.components if c.feature_id == t.requirement_ref]
        routes = [r.route_id for r in plan.api_routes if set(r.used_by) & set(sections)]
        links.append(PlanTestLink(test_id=t.test_id, targets=sections + routes))
    return links


def complete_data(plan: BuildPlan) -> None:
    """Code fixes for the data contract. Live runs left POST routes with no `used_by`, named sections by feature
    id, left out form rules and dashboard views, and added routes nothing calls; all of this follows from the
    sections, so code completes it instead of spending a fix round."""
    by_key: dict[str, list[str]] = {}
    for c in plan.components:
        for key in (c.section_id, c.feature_id, c.component_id):
            if key:
                by_key.setdefault(key, []).append(c.section_id)

    def resolve(keys: list[str]) -> list[str]:
        return list(dict.fromkeys(s for k in keys for s in by_key.get(k, [])))

    entities = {e.name: e for e in plan.data_entities}
    feature_of = {c.section_id: c.feature_id for c in plan.components}

    for r in plan.api_routes:
        r.route_id, r.used_by = f"{r.method} {r.path}", resolve(r.used_by)
    plan.api_routes = [r for r in plan.api_routes if r.entity in entities]   # a route must use a stored type
    routes = {r.route_id: r for r in plan.api_routes}
    by_path = {(r.method, r.path): r.route_id for r in plan.api_routes}
    rules = []
    for rule in plan.form_rules:
        sections = resolve([rule.section_id])
        method, _, path = rule.route_id.partition(" ")
        rule.route_id = by_path.get((method, path), rule.route_id)
        if sections and rule.route_id in routes:
            rule.section_id = sections[0]
            rules.append(rule)
    plan.form_rules = rules

    def entity_serves(r, sid):
        return feature_of.get(sid) in entities[r.entity].feature_ids

    for sid in form_sections(plan):
        if any(r.section_id == sid for r in plan.form_rules):
            continue
        posts = [r for r in plan.api_routes if r.method == "POST"]
        unclaimed = [r for r in posts if not r.used_by]
        route = (next((r for r in posts if sid in r.used_by), None)
                 or next((r for r in posts if entity_serves(r, sid)), None)
                 or (unclaimed[0] if len(unclaimed) == 1 else None))
        if route is None:
            continue
        if sid not in route.used_by:
            route.used_by.append(sid)
        required = {f.name for f in entities[route.entity].fields if f.required}
        plan.form_rules.append(FormRule(section_id=sid, route_id=route.route_id,
                                        required_fields=[f for f in route.request_fields if f in required]))
    for sid in live_sections(plan):
        if not any(sid in r.used_by for r in plan.api_routes):
            route = next((r for r in plan.api_routes if r.method == "GET" and entity_serves(r, sid)), None)
            if route:
                route.used_by.append(sid)

    plan.api_routes = [r for r in plan.api_routes if r.used_by]
    used = {r.entity for r in plan.api_routes}
    while extra := {link for e in plan.data_entities if e.name in used for link in e.links} - used:
        used |= extra                                         # booking -> class -> trainer keeps all three (KI-11)
    plan.data_entities = [e for e in plan.data_entities if e.name in used]
    plan.form_rules = [r for r in plan.form_rules if r.route_id in {x.route_id for x in plan.api_routes}]
    kept = {e.name for e in plan.data_entities}
    plan.dashboard_views = [v for v in plan.dashboard_views if v.entity in kept]
    viewed = {v.entity for v in plan.dashboard_views}
    plan.dashboard_views += [
        DashboardView(entity=e.name, title=e.name.replace("_", " ").capitalize(),
                      columns=[f.name.replace("_", " ").capitalize() for f in e.fields], statuses=["New", "Done"],
                      default_status="New")
        for e in plan.data_entities if e.name not in viewed and any(f.personal for f in e.fields)]


def build_plan(brief: ClarifiedBrief, retrieval: RetrievalResult, site: SiteDesign, data: DataDesign | None,
               cat: Catalogue, old_texts: list[TextSlot] | None = None) -> BuildPlan:
    pages = [p.model_copy(deep=True) for p in site.pages]
    specs = {s.spec_id: _spec(s, {p.page_id for p in pages}) for s in site.custom_specs}
    comps = _components(site, brief, cat, specs)
    _together_pages(site, pages, comps)
    for p in pages:
        p.section_ids = [c.section_id for c in sorted(comps, key=lambda c: c.order) if c.page == p.page_id]
    data = data or DataDesign()
    plan = BuildPlan(
        brief_version=brief.version, pages=pages, footer_links=site.footer_links, components=comps,
        custom_specs=list(specs.values()), theme=dict(brief.theme or {}),
        content_schema=derive_content_schema(comps, specs), texts=_text_slots(comps, specs, old_texts or []),
        data_entities=data.entities, api_routes=data.routes, dashboard_views=data.dashboard_views,
        form_rules=[r.model_copy(deep=True) for r in data.form_rules],
        not_built=[NotBuilt(asked=u.asked, reason=u.reason, alternative=u.alternative_text) for u in brief.unsupported],
        assumptions=[Assumption(text=u, reason="Chosen while planning the site") for u in site.unsure],
    )
    complete_data(plan)
    entities = {e.name: e for e in plan.data_entities}
    routes = {r.route_id: r for r in plan.api_routes}
    slot_ids = {t.slot_id for t in plan.texts}
    for rule in plan.form_rules:                        # fixed privacy rule (plan v2 §4, decision 16)
        entity = entities.get(routes[rule.route_id].entity or "") if rule.route_id in routes else None
        rule.consent_required = bool(entity and any(f.personal for f in entity.fields))
        success = f"{rule.section_id}.successMessage"
        rule.success_slot = success if success in slot_ids else None
    plan.execution_order = _work_plan(plan)
    plan.test_map = _test_map(brief, plan)
    return plan


def needs_data(plan: BuildPlan) -> bool:
    """Call 2 runs only for sites that send or show stored data."""
    return bool(form_sections(plan) or live_sections(plan))


def component_inputs(component_ids: list[str]) -> dict[str, list[dict]]:
    """Each found component's inputs for the site design call: names, kinds and allowed setting values."""
    needs = load_needs()
    return {cid: [{"name": n["name"], "kind": n["kind"], **({"type": n["type"]} if n["kind"] == "setting" else {})}
                  for n in needs.get(cid, {}).get("needs", []) if n["kind"] != "code"]
            for cid in component_ids}
