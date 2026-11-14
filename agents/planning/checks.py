# D:\FYP\FORGE-1\agents\planning\checks.py
"""
The 19 checks every Build Plan must pass (plan v2 §8). Each problem is one plain sentence, so the same list
is shown to the model in a fix round and written to the error log when planning stops.
"""
import re

from agents.catalogue import Catalogue
from agents.planning import fixed, texts
from agents.planning.assemble import form_sections, live_sections
from agents.planning.content_schema import needs_of, section_keys
from agents.state import BuildPlan, ClarifiedBrief, Limits, RetrievalResult

_FORBIDDEN = ("login", "password", "payment", "checkout", "card_number", "auth", "account")
_REAL_DETAIL = re.compile(r"[\w.+-]+@[\w-]+\.\w+|https?://|www\.|\+?\d[\d\s-]{6,}\d")


def _structure(plan: BuildPlan, brief: ClarifiedBrief, retrieval: RetrievalResult, cat: Catalogue,
               limits: Limits) -> list[str]:
    out = []
    pages = {p.page_id: p for p in plan.pages}
    routes = [p.route for p in plan.pages]
    # 1. Home, unique URLs, reachable (no page cap, D-212)
    if not any(p.page_id == "home" and p.route == "/" for p in plan.pages):
        out.append("1: there is no Home page with route '/'")
    out += [f"1: route {r} is used by two pages" for r in sorted({r for r in routes if routes.count(r) > 1})]
    if len(pages) != len(plan.pages):
        out.append("1: two pages share a page_id")
    reachable = {p.page_id for p in plan.pages if p.in_menu} | set(plan.footer_links)
    out += [f"1: page '{p.page_id}' is in neither the menu nor the footer" for p in plan.pages
            if p.page_id not in reachable and "[" not in p.route]
    # 2. one header, one footer, hero first on Home
    for sid, cid, _ in fixed.LAYOUT:
        if sum(c.component_id == cid for c in plan.components) != 1:
            out.append(f"2: there must be exactly one {cid}")
    home = pages.get("home")
    if home and (not home.section_ids or home.section_ids[0] != fixed.HERO[0]):
        out.append("2: the hero banner must be the first section of Home")
    # 3. every must feature has a section, no feature twice on a page
    placed = {c.feature_id for c in plan.components}
    out += [f"3: must feature '{f.id}' has no section" for f in fixed.planned_features(brief)
            if f.priority == "must" and f.id not in placed]
    seen = set()
    for c in plan.components:
        if (c.page, c.feature_id) in seen and c.page != "all":
            out.append(f"3: feature '{c.feature_id}' appears twice on page '{c.page}'")
        seen.add((c.page, c.feature_id))
    # 4. real components found for the feature, or custom; custom limit; sections on real pages
    found = {(x.feature_id, x.component_id) for x in retrieval.candidates}
    specs = {s.spec_id for s in plan.custom_specs}
    for c in plan.components:
        if c.page != "all" and c.page not in pages:
            out.append(f"4: section '{c.section_id}' is on page '{c.page}', which does not exist")
        if c.custom:
            if c.custom_spec_id not in specs:
                out.append(f"4: custom section '{c.section_id}' has no spec")
        elif c.role == "feature" and (c.feature_id, c.component_id) not in found \
                and c.component_id not in [extra for _, extra, _ in fixed.TOGETHER.values()]:
            out.append(f"4: '{c.component_id}' was not found for feature '{c.feature_id}'")
        elif c.component_id not in cat.components and c.component_id not in fixed.CODE_PART_NAMES:
            out.append(f"4: '{c.component_id}' is not a catalogue component")
    if len(plan.custom_specs) > limits.max_custom_features:
        out.append(f"4: {len(plan.custom_specs)} custom parts, at most {limits.max_custom_features}")
    # 5. nothing from the "not included" list
    for s in plan.custom_specs:
        text = " ".join((s.name, s.purpose, *s.behaviour)).lower()
        for cap in cat.capabilities.values():
            hit = next((p for p in cap.phrases if re.search(rf"(?<!\w){re.escape(p.lower())}(?!\w)", text)), None)
            if hit:
                out.append(f"5: custom part '{s.spec_id}' plans '{hit}', which FORGE cannot build")
    return out


def _completeness(plan: BuildPlan, with_texts: bool, rules: texts.TextRules | None) -> list[str]:
    out = []
    specs = {s.spec_id: s for s in plan.custom_specs}
    fields = {f.key for f in plan.content_schema}
    slots = {t.slot_id: t for t in plan.texts}
    served = {sid for r in plan.api_routes for sid in r.used_by}
    pages_in_menu = [p for p in plan.pages if p.in_menu]
    # 6. no empty component
    for c in plan.components:
        keys = {n["name"]: k for n, k in section_keys(c, specs)}
        for n in needs_of(c, specs):
            if not n.get("required", True):
                continue
            kind, where = n["kind"], f"'{c.section_id}' input '{n['name']}'"
            if kind == "copy" and (f"{c.section_id}.{n['name']}" not in slots or
                                   (with_texts and not slots[f"{c.section_id}.{n['name']}"].text.strip())):
                out.append(f"6: {where} has no text")
            elif kind in ("fact", "list", "image") and keys.get(n["name"]) not in fields:
                out.append(f"6: {where} is not in the business details form")
            elif kind == "live" and c.section_id not in served:
                out.append(f"6: {where} needs live data, but no API route serves this section")
            elif kind == "setting" and n.get("source") == "plan":
                if c.component_id == "navbar" and not pages_in_menu or c.component_id == "footer" and not plan.footer_links:
                    out.append(f"6: {where} has no links")
    # 7. text passes the pitch rules
    if with_texts and rules:
        out += [f"7: text '{sid}': {'; '.join(p)}"
                for sid, p in texts.check_all(plan.texts, rules, relevance=False).items()]
    return out


def _data(plan: BuildPlan, limits: Limits) -> list[str]:
    out = []
    entities = {e.name: e for e in plan.data_entities}
    routes = {r.route_id: r for r in plan.api_routes}
    sections = {c.section_id for c in plan.components}
    forms = form_sections(plan)
    rules = {r.section_id: r for r in plan.form_rules}
    # 8. every form posts to a route, every route is used
    for sid in forms:
        rule = rules.get(sid)
        if not rule or rule.route_id not in routes or routes[rule.route_id].method != "POST":
            out.append(f"8: form '{sid}' does not post to a POST route of the API contract")
    for r in plan.api_routes:
        if not r.used_by or any(s not in sections for s in r.used_by):
            out.append(f"8: route '{r.route_id}' is not used by a planned section")
        if r.route_id != f"{r.method} {r.path}":
            out.append(f"8: route id '{r.route_id}' must be '{r.method} {r.path}'")
    # 9. routes use defined types, links point to real types
    for r in plan.api_routes:
        e = entities.get(r.entity or "")
        if not e:
            out.append(f"9: route '{r.route_id}' uses no defined data type")
            continue
        names = {f.name for f in e.fields}
        out += [f"9: route '{r.route_id}' sends '{f}', which '{e.name}' does not have"
                for f in r.request_fields if f not in names]
    for e in plan.data_entities:
        out += [f"9: '{e.name}' links to '{link}', which is not defined" for link in e.links if link not in entities]
    if len(entities) != len(plan.data_entities):
        out.append("9: two data types share a name")
    # 10. no forms and no live data: no data model and no API
    if not forms and not live_sections(plan) and (plan.data_entities or plan.api_routes):
        out.append("10: the site sends and shows no data, so it must have no data model and no API")
    # 11. personal data: consent tick box and a dashboard view
    views = {v.entity for v in plan.dashboard_views}
    for rule in plan.form_rules:
        route = routes.get(rule.route_id)
        e = entities.get(route.entity or "") if route else None
        if e and any(f.personal for f in e.fields):
            if not rule.consent_required:
                out.append(f"11: form '{rule.section_id}' collects personal data without a consent tick box")
            if e.name not in views:
                out.append(f"11: '{e.name}' holds visitor submissions but has no dashboard view")
    # 12. size caps; no logins or payments
    if len(plan.data_entities) > limits.max_data_entities:
        out.append(f"12: {len(plan.data_entities)} data types, at most {limits.max_data_entities}")
    if len(plan.api_routes) > limits.max_api_routes:
        out.append(f"12: {len(plan.api_routes)} routes, at most {limits.max_api_routes}")
    names = [e.name for e in plan.data_entities] + [r.path for r in plan.api_routes]
    out += [f"12: '{n}' looks like a login or payment, which FORGE cannot build" for n in names
            if any(w in n.lower() for w in _FORBIDDEN)]
    return out


def _safety(plan: BuildPlan, brief: ClarifiedBrief) -> list[str]:
    out = []
    targets = {c.section_id for c in plan.components} | {r.route_id for r in plan.api_routes}
    linked = {t.test_id: t for t in plan.test_map}
    # 13. every acceptance test linked to something that can satisfy it
    for t in brief.test_cases:
        link = linked.get(t.test_id)
        if not link or not link.targets or any(x not in targets for x in link.targets):
            out.append(f"13: test {t.test_id} ('{t.requirement_ref}') has no section or route that can satisfy it")
    # 14. the theme is exactly the user's
    if plan.theme != (brief.theme or {}):
        out.append("14: the theme differs from the one the user chose")
    # 15. no real business details anywhere in the plan's own words
    words = [p.title for p in plan.pages] + [p.purpose for p in plan.pages] + [t.text for t in plan.texts]
    words += [x for s in plan.custom_specs for x in (s.name, s.purpose, s.ui_notes, *s.behaviour)]
    if any(_REAL_DETAIL.search(w) for w in words):
        out.append("15: the plan contains a real contact detail; facts come only from the business details form")
    # 16. work plan: no loops, no file owned twice
    deps = {t.task_id: [d for d in t.depends_on] for t in plan.execution_order}
    if any(d not in deps for ds in deps.values() for d in ds) or _has_loop(deps):
        out.append("16: the work plan has a loop or depends on an unknown task")
    owned = [o for t in plan.execution_order for o in t.owns]
    if len(owned) != len(set(owned)):
        out.append("16: a file or folder is owned by two agents")
    return out


def _has_loop(deps: dict[str, list[str]]) -> bool:
    done, visiting = set(), set()

    def visit(n: str) -> bool:
        if n in done:
            return False
        if n in visiting:
            return True
        visiting.add(n)
        if any(visit(d) for d in deps.get(n, [])):
            return True
        visiting.discard(n)
        done.add(n)
        return False

    return any(visit(n) for n in deps)


def _seo_and_access(plan: BuildPlan, with_texts: bool) -> list[str]:
    """17: every page has a search title (unique) and description; 18: every page has exactly one H1 (D-221)."""
    out = []
    texts_by_id = {t.slot_id: t.text.strip() for t in plan.texts}
    titles: dict[str, str] = {}
    for p in plan.pages:
        head = f"{p.page_id}.{fixed.SEO[0]}"
        if not any(c.section_id == head for c in plan.components):
            out.append(f"17: page '{p.page_id}' has no search title and description")
        elif with_texts:
            title, description = texts_by_id.get(f"{head}.title", ""), texts_by_id.get(f"{head}.description", "")
            if not title or not description:
                out.append(f"17: page '{p.page_id}' needs a search title and description")
            elif title.lower() in titles and "[" not in p.route:
                out.append(f"17: page '{p.page_id}' has the same search title as '{titles[title.lower()]}'")
            titles.setdefault(title.lower(), p.page_id)
        if "[" in p.route:
            continue                                  # one page per item: its H1 is the item's own title
        h1 = sum(c.page == p.page_id and c.component_id in fixed.H1_PARTS for c in plan.components)
        if h1 != 1:
            out.append(f"18: page '{p.page_id}' has {h1} main headings (H1); it needs exactly one")
    return out


def _variety(plan: BuildPlan, limits: Limits) -> list[str]:
    """19: the design direction was chosen for this site, and at most a few sections are written fresh (D-224)."""
    out = []
    if not plan.direction.chosen:
        out.append("19: no design direction was chosen for this site (density, corners, type, surfaces, rhythm, images, "
                   "headings, hero and footer layout)")
    showcase = [c.section_id for c in plan.components if c.showcase]
    if len(showcase) > limits.max_showcase_sections:
        out.append(f"19: {len(showcase)} sections are marked to be written fresh, at most {limits.max_showcase_sections}")
    return out


def run_checks(plan: BuildPlan, brief: ClarifiedBrief, retrieval: RetrievalResult, cat: Catalogue, limits: Limits,
               with_texts: bool = False) -> list[str]:
    """All problems, each prefixed with its check number. Check 7 (text) runs once the text is written."""
    rules = texts.rules_for(brief, plan) if with_texts else None
    return (_structure(plan, brief, retrieval, cat, limits) + _completeness(plan, with_texts, rules)
            + _data(plan, limits) + _safety(plan, brief) + _seo_and_access(plan, with_texts) + _variety(plan, limits))
