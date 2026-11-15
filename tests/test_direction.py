"""Design direction dealt by code (D-239). No model calls."""
from collections import Counter
from itertools import combinations

import pytest

from agents.planning import direction as d
from agents.state import DesignDirection


@pytest.fixture(autouse=True)
def _fresh_rotation():
    d.forget_recent()
    yield
    d.forget_recent()


def test_every_preset_uses_real_options_inside_its_family_range():
    real = {f: set(DesignDirection.model_fields[f].annotation.__args__) for f in d.FIELDS}
    for name, fam in d.load().items():
        assert set(fam["allowed"]) == set(d.FIELDS), name
        for f, values in fam["allowed"].items():
            assert set(values) <= real[f], (name, f)
        assert len(fam["presets"]) >= 3, name
        for p in fam["presets"]:
            assert 4 <= len(p["fixed"]) <= 5, p["id"]
            assert all(v in fam["allowed"][f] for f, v in p["fixed"].items()), p["id"]


def test_presets_of_a_family_share_at_most_three_fixed_choices():
    for name, fam in d.load().items():
        for a, b in combinations(fam["presets"], 2):
            shared = [f for f in a["fixed"] if b["fixed"].get(f) == a["fixed"][f]]
            assert len(shared) <= 3, (a["id"], b["id"], shared)


@pytest.mark.parametrize("business, family", [
    ("bakery", "food"), ("Italian restaurant", "food"), ("hair salon", "beauty"), ("law firm", "professional"),
    ("accounting firm", "professional"), ("plumbing business", "trades"), ("clothing boutique", "retail"),
    ("gym", "fitness_events"), ("NGO running village schools", "education_community"),
    ("wedding photographer", "creative_personal"), ("space tourism", "general"), (None, "general"),
])
def test_business_types_go_to_their_family(business, family):
    assert d.family_of(business) == family


def test_rotation_deals_every_preset_before_repeating_one():
    picks = [d.start("restaurant", f"site-{i}")["preset"] for i in range(4)]
    assert len(set(picks)) == 4


def test_many_sites_spread_over_presets_and_open_choices():
    starts = [d.start("café", f"site-{i}") for i in range(100)]
    presets = Counter(s["preset"] for s in starts)
    assert len(presets) == 4 and max(presets.values()) - min(presets.values()) <= 2
    allowed = d.load()["food"]["allowed"]
    for f in d.FIELDS:
        assert {s["direction"][f] for s in starts} == set(allowed[f]), f


def test_the_same_seed_draws_the_same_open_choices():
    a = d.start("café", "same-site")
    d.forget_recent()
    assert d.start("café", "same-site") == a


def test_measured_reference_choices_are_dealt_and_locked():
    s = d.start("café", "x", {"corners": "sharp", "images": "square", "site": "craigslist.org"})
    assert s["direction"]["corners"] == "sharp" and s["direction"]["images"] == "square"
    assert s["locked"] == ["corners", "images"]


def _begin(**direction):
    base = {"density": "airy", "corners": "soft", "type_scale": "calm", "surfaces": "cards", "rhythm": "alternating",
            "images": "rounded", "headings": "eyebrow", "hero_variant": "split"}
    return {"direction": base | direction, "allowed": d.load()["professional"]["allowed"], "locked": ["images"]}


def test_the_model_keeps_at_most_two_reasoned_changes_inside_the_range():
    begin = _begin()
    model = begin["direction"] | {"density": "balanced", "type_scale": "expressive", "surfaces": "flat",
                                  "corners": "round", "images": "square", "headings": "plain"}
    reasons = {"density": "many services", "type_scale": "bold brand", "surfaces": "minimal firm",
               "corners": "friendly", "images": "editorial"}            # headings has no reason
    out, kept = d.settle(model, begin, reasons, pages=5)
    assert [k["field"] for k in kept] == ["density", "type_scale"]
    assert out["surfaces"] == "cards"                    # a third change goes back to the start
    assert out["corners"] == "soft"                      # round is outside the professional range
    assert out["images"] == "rounded"                    # locked by the reference
    assert out["headings"] == "eyebrow"                  # a change without a reason is not kept


def test_a_round_corner_outside_the_range_does_not_use_up_a_change():
    out, kept = d.settle(_begin() | {}, _begin(), {}, pages=2)
    assert kept == [] and out["footer_variant"] == "centred"
    model = _begin()["direction"] | {"corners": "round", "density": "balanced", "hero_variant": "editorial"}
    out, kept = d.settle(model, _begin(), {"corners": "x", "density": "y", "hero_variant": "z"}, pages=6)
    assert [k["field"] for k in kept] == ["density", "hero_variant"] and out["footer_variant"] == "columns"
