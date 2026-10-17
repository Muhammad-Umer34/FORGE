"""Grounding rules (v6 Section 9, D-113, D-134). No model calls."""
from agents.catalogue import load_catalogue
from agents.clarification import grounding, slots
from agents.clarification.schemas import IntakeItem
from agents.state import ClarificationState, Limits, RequestedItem

CAT = load_catalogue()


def state(**kwargs) -> ClarificationState:
    return ClarificationState(slots=slots.init_slots(), **kwargs)


def item(item_id="i1", text="thing", **kwargs) -> RequestedItem:
    return RequestedItem(item_id=item_id, text=text, evidence=text, **kwargs)


def test_evidence_must_appear_in_user_text():
    assert grounding.evidence_found("show our menu", "Please show our menu and prices")
    assert grounding.evidence_found("menu prices", "show our menu and the prices")
    assert not grounding.evidence_found("online booking", "a bakery website with a menu")
    assert not grounding.evidence_found("", "anything")


def test_items_without_evidence_are_dropped():
    c = state()
    raw = [IntakeItem(text="menu", kind="feature", evidence="our menu", candidate_feature_id="menu-catalog"),
           IntakeItem(text="booking", kind="feature", evidence="book a table", candidate_feature_id="booking")]
    flags = grounding.items_from_model(c, raw, "a bakery site with our menu")
    assert [i.text for i in c.requested_items] == ["menu"]
    assert flags and flags[0].startswith("dropped_unverified_item")


def test_each_item_gets_one_resolution():
    c = state(requested_items=[
        item("i1", "our menu", candidate_feature_id="menu-catalog"),
        item("i2", "card payments", candidate_capability_id="online-payments"),
        item("i3", "a way to reach us", candidate_feature_id="contact-form", alternative_feature_id="booking"),
        item("i4", "actually no blog", candidate_feature_id="blog", retracted=True),
        item("i5", "warm colours", kind="style"),
        item("i6", "sync with Zentrix Planner", kind="integration"),
        item("i7", "a cake designer tool"),
        item("i8", "fake id", candidate_feature_id="not-a-real-feature"),
    ])
    grounding.ground_items(c, CAT)
    res = {i.item_id: (i.resolution, i.resolved_to) for i in c.requested_items}
    assert res["i1"] == ("feature", "menu-catalog")
    assert res["i2"] == ("unsupported", "online-payments")
    assert res["i3"][0] == "ambiguous"
    assert res["i4"][0] == "dropped_by_user"
    assert res["i5"] == ("noted", "style")
    assert res["i6"] == ("unsupported", None)
    assert res["i7"][0] == "custom"
    assert res["i8"][0] == "custom"          # an invented id is never trusted
    assert [m.feature_id for m in c.matches] == ["menu-catalog"]
    assert "custom_item" in c.risk_flags


def test_the_website_itself_is_never_a_custom_feature():
    c = state(business_type="shop", requested_items=[item("i1", "website for my shop"), item("i2", "a cake designer tool")])
    grounding.ground_items(c, CAT)
    assert c.requested_items[0].resolution == "noted"
    assert c.requested_items[1].resolution == "custom"


def test_unsupported_phrase_safety_net_only_without_a_feature_match():
    c = state(requested_items=[item("i1", "a shopping cart"), item("i2", "a WhatsApp button", candidate_feature_id="whatsapp-chat")])
    grounding.ground_items(c, CAT)
    assert c.requested_items[0].resolution == "unsupported"
    assert c.requested_items[1].resolution == "feature"


def test_baseline_is_a_template_not_a_limit():
    c = state()
    assert grounding.choose_baseline(c, CAT) == "brochure"
    c.is_business = False
    assert grounding.choose_baseline(c, CAT) is None          # e.g. a wedding site: allowed, no baseline
    grounding.add_match(c, CAT, "booking", "user_stated")
    assert grounding.choose_baseline(c, CAT) == "booking"
    c.baseline_hint = "portfolio"
    assert grounding.choose_baseline(c, CAT) == "portfolio"


def site(c) -> dict[str, str]:
    return dict(grounding.site_feature_ids(c, CAT))


def test_chosen_baseline_gets_its_core_feature():          # D-149
    c = state(baseline_hint="catalog")
    assert site(c)["product-grid"] == "baseline_default"
    grounding.add_match(c, CAT, "order-request", "user_delegated")   # an order form is not the main feature
    assert "product-grid" in site(c)
    c.business_type = "bakery"
    assert "menu-catalog" in site(c) and "product-grid" not in site(c)


def test_core_feature_is_not_added_when_present_or_removed():
    c = state(baseline_hint="catalog", business_type="bakery")
    grounding.add_match(c, CAT, "menu-catalog", "user_stated")
    assert [f for f in site(c) if f in ("product-grid", "menu-catalog")] == ["menu-catalog"]
    c2 = state(baseline_hint="catalog", removed_feature_ids=["product-grid"])
    assert "product-grid" not in site(c2) and "menu-catalog" not in site(c2)   # unticked stays unticked


def test_core_feature_for_booking_and_none_for_brochure():
    assert "booking" in site(state(baseline_hint="booking"))
    brochure = site(state(baseline_hint="brochure"))
    assert set(brochure) == {"about-story", "services-overview", "contact-info"}


def test_pages_start_with_home_and_follow_features():
    c = state()
    grounding.add_match(c, CAT, "menu-catalog", "user_stated")
    grounding.add_match(c, CAT, "order-request", "user_confirmed")
    pages = grounding.site_pages(c, CAT)
    assert pages[0] == "home"
    assert {"menu", "order", "contact"} <= set(pages)


def test_extras_fit_the_business_and_are_capped():
    c = state(business_type="bakery")
    grounding.propose_extras(c, CAT, Limits(max_extras_shown=3))
    assert 0 < len(c.proposed_extras) <= 3
    assert all(e.status == "pending" for e in c.proposed_extras)
    assert all(CAT.features[e.feature_id].inclusion == "suggest" for e in c.proposed_extras)
