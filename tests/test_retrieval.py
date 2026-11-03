"""Context Retrieval (plan v2, step 0): catalogue candidates per feature, code only (D-203)."""
from agents.catalogue import load_catalogue
from agents.retrieval.ranker import keyword_matches, rank_and_retrieve_components
from agents.state import BriefFeature, ClarifiedBrief


def feature(fid, tier="catalogued", name=None):
    return BriefFeature(id=fid, name=name or fid, priority="must", source="user_stated", tier=tier)


def candidates(brief):
    result = rank_and_retrieve_components(brief)
    out = {}
    for c in result.candidates:
        out.setdefault(c.feature_id, []).append((c.component_id, c.score))
    return out


def test_catalogued_features_get_every_component_of_that_feature():
    found = candidates(ClarifiedBrief(features=[feature("booking"), feature("gallery"), feature("blog"),
                                                feature("services-price-list")]))
    assert found["booking"] == [("booking-form", 1.0), ("appointment-slot-picker", 1.0)]
    assert {c for c, _ in found["gallery"]} == {"image-gallery", "gallery-carousel"}
    assert {c for c, _ in found["blog"]} == {"blog-list", "blog-post"}          # two parts used together
    assert found["services-price-list"] == [("services-price-list", 1.0)]


def test_custom_features_get_only_close_matches_best_first():
    found = candidates(ClarifiedBrief(features=[
        feature("custom-reviews", "custom", "customer reviews from happy clients"),
        feature("custom-price-list", "custom", "price list for haircuts"),
        feature("custom-loyalty", "custom", "loyalty stamp card"),
    ]))
    assert found["custom-reviews"][0][0] == "testimonials"
    assert found["custom-price-list"][0][0] == "services-price-list"   # its own name breaks the tie
    assert "custom-loyalty" not in found                                 # nothing fits: it stays custom
    assert all(len(v) <= 3 for v in found.values())


def test_unknown_and_unsupported_items_get_nothing():
    found = candidates(ClarifiedBrief(features=[feature("not-a-real-feature"),
                                                feature("online-payments", "unsupported")]))
    assert found == {}


def test_layout_parts_are_never_matched_to_a_custom_feature():
    cat = load_catalogue()
    assert all(c not in ("navbar", "footer") for c, _ in keyword_matches("menu bar footer links navigation", cat))


def test_the_catalogue_describes_every_component():
    cat = load_catalogue()
    assert len(cat.components) == 46
    booking = cat.components["booking-form"]
    assert booking.feature_id == "booking" and "availability" in booking.data_needs
    assert ("appointment-slot-picker", "Only the date and time slot chooser, without the full form.") in booking.not_for
