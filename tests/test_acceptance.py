"""Acceptance-test validation (v6 Section 13, D-119). No model calls."""
from agents.clarification.acceptance import validate_tests
from agents.clarification.schemas import GeneratedTest
from agents.state import BriefFeature, ClarifiedBrief, Limits

BRIEF = ClarifiedBrief(features=[
    BriefFeature(id="menu-catalog", name="Menu", priority="must", source="user_stated"),
    BriefFeature(id="order-request", name="Order request", priority="must", source="user_confirmed"),
    BriefFeature(id="about-story", name="About", priority="should", source="baseline_default"),
])


def draft(ref: str, kind: str = "happy_path", ears: str = "WHEN a visitor acts THE SYSTEM SHALL respond") -> GeneratedTest:
    return GeneratedTest(requirement_ref=ref, kind=kind, ears=ears, given="g", when="w", then="t",
                     check="form_submit" if ref == "order-request" else "element_present",
                     description=f"{ref} {kind}", expected_result="ok")


def test_complete_set_passes_with_ids():
    tests, issues = validate_tests([draft("menu-catalog"), draft("order-request"), draft("order-request", "negative")],
                                   BRIEF, Limits())
    assert issues == []
    assert [t.test_id for t in tests] == ["T01", "T02", "T03"]


def test_missing_coverage_is_reported():
    _, issues = validate_tests([draft("menu-catalog"), draft("order-request")], BRIEF, Limits())
    assert any("no negative test for form feature 'order-request'" in i for i in issues)


def test_tests_for_features_not_in_the_brief_are_dropped():
    tests, issues = validate_tests([draft("online-payments"), draft("menu-catalog"), draft("order-request"),
                                    draft("order-request", "negative")], BRIEF, Limits())
    assert all(t.requirement_ref != "online-payments" for t in tests)
    assert any("online-payments" in i for i in issues)


def test_bad_ears_form_is_rejected():
    _, issues = validate_tests([draft("menu-catalog", ears="The menu shows")], BRIEF, Limits())
    assert any("WHEN" in i for i in issues)


def test_trimming_keeps_coverage_first():
    many = [draft("about-story")] * 10 + [draft("menu-catalog"), draft("order-request"), draft("order-request", "negative")]
    tests, _ = validate_tests(many, BRIEF, Limits(max_test_cases=4))
    refs = [(t.requirement_ref, t.kind) for t in tests]
    assert len(tests) == 4
    assert ("menu-catalog", "happy_path") in refs and ("order-request", "negative") in refs
