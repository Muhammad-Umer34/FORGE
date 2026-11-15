"""The frontend agent's compiler (D-240): an approved plan in, the site's files out. No model calls, no Node."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_planning import built_plan  # noqa: E402

from agents.frontend_generator import compile_site, input_summary  # noqa: E402
from agents.frontend_generator.photos import Dealer  # noqa: E402


def _files():
    brief, plan = built_plan()
    return brief, plan, compile_site(plan, brief.business_type, "req-1")


def test_the_same_plan_and_seed_give_the_same_files():
    brief, plan, files = _files()
    assert compile_site(plan, brief.business_type, "req-1") == files


def test_one_page_per_route_plus_the_site_files():
    _, plan, files = _files()
    for page in plan.pages:
        assert ("app/page.tsx" if page.route == "/" else f"app{page.route}/page.tsx") in files
    for path in ("app/layout.tsx", "app/globals.css", "app/not-found.tsx", "app/sitemap.ts", "app/robots.ts",
                 "content/site.json"):
        assert path in files


def test_texts_land_in_their_props_and_no_placeholder_is_left():
    brief, plan, _ = _files()
    for t in plan.texts:
        if t.section_id == "home.hero" and t.prop == "headline":
            t.text = "Welcome to {business_name}"
    files = compile_site(plan, brief.business_type, "req-1")
    assert '"headline": "Welcome to Your Hair Salon"' in files["app/page.tsx"] or \
        f'"headline": "Welcome to {plan.sample_content["business_name"]}"' in files["app/page.tsx"]
    for content in files.values():
        assert not re.search(r'"[^"\n]*\{[a-z_]+\}[^"\n]*"', content), "a placeholder was left in a text"


def test_list_items_get_ids_and_links_point_at_real_pages():
    _, plan, files = _files()
    home = files["app/page.tsx"]
    assert '"id": "services-1"' in home and '"id": "services-2"' in home
    routes = {p.route for p in plan.pages}
    for href in re.findall(r'"[a-zA-Z]*(?:Href|Link)": "([^"]+)"', "".join(files.values())):
        assert href in routes or href.startswith("#section-"), href


def test_layout_carries_the_direction_and_menu_pages_in_order():
    _, plan, files = _files()
    layout, d = files["app/layout.tsx"], plan.direction
    for attr, value in (("density", d.density), ("corners", d.corners), ("type", d.type_scale),
                        ("surfaces", d.surfaces), ("rhythm", d.rhythm), ("images", d.images),
                        ("headings", d.headings)):
        assert f'data-{attr}="{value}"' in layout
    menu = sorted((p for p in plan.pages if p.in_menu), key=lambda p: p.menu_order)
    positions = [layout.index(f'"href": "{p.route}"') for p in menu]
    assert positions == sorted(positions)


def test_theme_tokens_and_seo_metadata():
    _, plan, files = _files()
    css = files["app/globals.css"]
    for name, value in plan.theme["tokens"]["light"].items():
        assert f"--{name}: {value};" in css
    seo = {(t.section_id, t.prop): t.text for t in plan.texts}
    assert json.dumps(seo[("home.seo", "title")]) in files["app/page.tsx"]


def test_a_custom_part_becomes_its_fallback_section():
    _, _, files = _files()
    assert "<CtaBanner" in files["app/page.tsx"]


def test_photos_do_not_repeat_within_a_site():
    dealer = Dealer("food", "req-1")
    picks = [dealer.photo() for _ in range(5)]
    assert len(set(picks)) == len(picks) or all(p.startswith("data:image/svg") for p in picks)


def test_settings_are_shaped_to_their_type():
    from agents.frontend_generator.compiler import _setting
    assert _setting({"type": "2 | 3 | 4"}, "3") == 3                      # found live: the planner wrote "3"
    assert _setting({"type": "2 | 3 | 4"}, "7") is None                   # not allowed: the default applies
    assert _setting({"type": '"split" | "centred"'}, "split") == "split"
    assert _setting({"type": "boolean"}, "true") is True


def test_input_summary_lists_pages_sections_and_direction():
    brief, plan, _ = _files()
    s = input_summary(plan, brief.business_type)
    assert [p["route"] for p in s["pages"]] == [p.route for p in plan.pages]
    assert s["direction"]["hero_variant"] == plan.direction.hero_variant
    assert all(sec["component"] != "seo-head" for p in s["pages"] for sec in p["sections"])
