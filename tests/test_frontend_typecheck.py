"""Every catalogue component, given props by the frontend compiler, passes the TypeScript check (D-240). Slow: it
runs the real build worker, so it needs site_template/node_modules (`npm install` there once)."""
import re

import pytest

from agents import build_worker
from agents.frontend_generator import compile_site
from agents.planning.content_schema import derive_content_schema, load_needs, sample_content
from agents.state import BuildPlan, DesignDirection, PlannedComponent, PlannedPage

pytestmark = pytest.mark.skipif(not (build_worker.TEMPLATE / "node_modules" / "next").is_dir(),
                                reason="site_template packages not installed")
SITE_WIDE = {"navbar", "footer", "not-found-page", "whatsapp-button", "cookie-notice", "back-to-top",
             "announcement-bar", "lead-capture-popup"}


def every_component_plan() -> BuildPlan:
    """One page holding every catalogue component, the way the planner would place them."""
    ids = sorted(c for c, e in load_needs().items() if isinstance(e, dict) and e.get("in_catalogue", True))
    needs = load_needs()
    # Settings as the planner writes them: strings, even where the type is a number or boolean (found live: "3").
    settings = {c: {n["name"]: str(re.findall(r'"([^"]+)"|(\d+)', n["type"])[0][0] or
                                   re.findall(r'"([^"]+)"|(\d+)', n["type"])[0][1])
                    for n in needs[c]["needs"] if n["kind"] == "setting" and "|" in n.get("type", "")}
                for c in ids}
    comps = [PlannedComponent(section_id=f"{'all' if c in SITE_WIDE else 'home'}.{c}", component_id=c,
                              page="all" if c in SITE_WIDE else "home", order=i, settings=settings[c],
                              role="layout" if c in SITE_WIDE else "feature") for i, c in enumerate(ids)]
    schema = derive_content_schema(comps, {})
    page = PlannedPage(page_id="home", route="/", title="Home",
                       section_ids=[c.section_id for c in comps if c.page == "home"])
    contact = PlannedPage(page_id="contact", route="/contact", title="Contact", menu_order=1)
    return BuildPlan(pages=[page, contact], footer_links=["home", "contact"], components=comps,
                     content_schema=schema, sample_content=sample_content(schema, "bakery"),
                     direction=DesignDirection(chosen=True))


def test_every_component_type_checks_with_compiled_props():
    files = compile_site(every_component_plan(), "bakery", "typecheck")
    result = build_worker.build(files, build_id="test-every-component")
    typecheck = result.steps[0]
    assert typecheck.ok, "\n".join(f"{i.file}:{i.line} {i.message}" for i in typecheck.issues[:40]) or typecheck.output
