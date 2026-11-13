"""Brief assembly, clarified text, code checks, repair and confirmation (v6 Sections 10-12). No model calls."""
from agents.catalogue import load_catalogue
from agents.clarification import brief as briefs
from agents.clarification import grounding, slots
from agents.state import BriefFeature, ClarificationState, Limits, RequestedItem

CAT = load_catalogue()
LIMITS = Limits()


def bakery() -> ClarificationState:
    c = ClarificationState(slots=slots.init_slots(), business_type="bakery", goal="Show the menu and take pre-orders",
                           requested_items=[
                               RequestedItem(item_id="i1", text="our menu", candidate_feature_id="menu-catalog"),
                               RequestedItem(item_id="i2", text="card payments", candidate_capability_id="online-payments"),
                           ])
    grounding.ground_items(c, CAT)
    for name, values in (("purpose", ["bakery"]), ("visitor_actions", ["order-request"])):
        s = slots.get_slot(c, name)
        s.status, s.values, s.source = "answered", values, "user_confirmed"
    grounding.add_match(c, CAT, "order-request", "user_confirmed")
    return c


def test_draft_contains_requested_and_default_features():
    b = briefs.draft_brief(bakery(), CAT)
    by_id = {f.id: f for f in b.features}
    assert b.baseline == "catalog"
    assert by_id["menu-catalog"].priority == "must" and by_id["order-request"].priority == "must"
    assert by_id["about-story"].source == "baseline_default" and by_id["about-story"].priority == "should"
    assert "navigation" not in by_id                  # layout parts are added by Planning
    assert b.pages[0]["name"] == "home"
    assert set(b.content_needs) <= set(CAT.content_keys)
    assert [u.capability_id for u in b.unsupported] == ["online-payments"]


def test_clarified_text_only_states_what_is_in_the_brief():
    b = briefs.draft_brief(bakery(), CAT)
    text = b.clarified_text
    assert text.startswith(f"A {len(b.pages)}-page website for a bakery.")
    assert "send an order request" in text
    assert 'Not included: "card payments"' in text


def test_code_checks_pass_for_a_good_brief():
    c = bakery()
    assert briefs.code_checks(briefs.draft_brief(c, CAT), c, CAT, LIMITS) == []


def test_code_checks_catch_unanswered_slot_and_open_item():
    c = bakery()
    slots.get_slot(c, "visitor_actions").status = "missing"
    c.requested_items.append(RequestedItem(item_id="i9", text="a thing", resolution="ambiguous"))
    issues = briefs.code_checks(briefs.draft_brief(c, CAT), c, CAT, LIMITS)
    assert any("visitor_actions" in i for i in issues)
    assert any("unresolved requested items" in i for i in issues)


def test_repair_drops_duplicates():
    c = bakery()
    b = briefs.draft_brief(c, CAT)
    b.features.append(BriefFeature(id="menu-catalog", name="dup", priority="must", source="user_stated"))
    assert "duplicate features" in briefs.code_checks(b, c, CAT, LIMITS)
    assert briefs.code_checks(briefs.repair(b, c), c, CAT, LIMITS) == []


def test_confirmation_screen():
    c = bakery()
    grounding.propose_extras(c, CAT, LIMITS)
    b = briefs.draft_brief(c, CAT)
    screen = briefs.confirmation_payload(b, c, LIMITS, edit_allowed=True)
    assert screen["type"] == "confirmation"
    assert screen["limits_notice"] and screen["limits_notice"][0]["asked"] == "card payments"
    assert all(f["can_untick"] == (f["source"] == "baseline_default") for f in screen["features"])
    assert len(screen["extras"]) == len(c.proposed_extras)
    assert "edit" in screen["actions"]
    assert briefs.confirmation_payload(b, c, LIMITS, edit_allowed=False)["actions"] == ["confirm", "cancel", "theme_source"]
    c.theme_source_tries = {"logo": 3, "screenshot": 3, "website": 3}                 # every source used up (D-169)
    after = briefs.confirmation_payload(b, c, LIMITS, edit_allowed=False)
    assert after["actions"] == ["confirm", "cancel"] and not any(after["theme_sources_left"].values())


def test_custom_ids_never_collide_for_urdu_or_emoji_names():          # KI-06
    c = bakery()
    c.requested_items += [RequestedItem(item_id="i7", text="آن لائن کیک ڈیزائن", resolution="custom"),
                          RequestedItem(item_id="i8", text="🎂🎉", resolution="custom"),
                          RequestedItem(item_id="i9", text="Cake builder", resolution="custom"),
                          RequestedItem(item_id="i10", text="cake builder!", resolution="custom")]
    custom = [f.id for f in briefs.draft_brief(c, CAT).features if f.tier == "custom"]
    assert custom == ["custom-i7", "custom-i8", "custom-cake-builder", "custom-cake-builder-i10"]


def test_a_large_site_has_no_page_limit():                            # KI-05, D-212
    c = bakery()
    for fid in ("faq", "legal-pages", "blog", "events", "gallery", "testimonials", "booking", "team"):
        if fid in CAT.features:
            grounding.add_match(c, CAT, fid, "user_stated")
    b = briefs.draft_brief(c, CAT)
    assert len(b.pages) > 10
    assert not [i for i in briefs.code_checks(b, c, CAT, LIMITS) if "page" in i]
    assert not [g for g in slots.open_gaps(c, CAT, LIMITS) if g.key == "page_limit"]


def test_audience_and_the_users_notes_reach_the_brief():                  # D-219, KI-09, SL-06
    c = bakery()
    c.audience = "office workers in Gulberg"
    c.requested_items += [RequestedItem(item_id="i5", text="show our prices", kind="content"),
                          RequestedItem(item_id="i6", text="soft pastel look", kind="style")]
    grounding.ground_items(c, CAT)
    b = briefs.draft_brief(c, CAT)
    assert b.audience == "office workers in Gulberg" and "For: office workers in Gulberg." in b.clarified_text
    assert b.content_notes == ["show our prices"] and b.style_notes == ["soft pastel look"]
