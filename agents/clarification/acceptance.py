# D:\FYP\FORGE-1\agents\clarification\acceptance.py
"""
Acceptance-test validation (code, no model) - decisions D-119, D-120.
The test-generation call sees only the confirmed brief. This module checks what came back:
every test cites a real feature, nothing tests an unsupported item, every 'must' feature has a
happy path, every form has a negative test, and the total stays within the limit.
"""
from agents.clarification.schemas import GeneratedTest
from agents.state import AcceptanceTest, ClarifiedBrief, Limits

# Features where visitors submit something (need a negative test, e.g. required field empty).
FORM_FEATURES = {"contact-form", "order-request", "booking", "newsletter", "lead-capture"}


def validate_tests(drafts: list[GeneratedTest], brief: ClarifiedBrief, limits: Limits) -> tuple[list[AcceptanceTest], list[str]]:
    """Return (tests, issues). Issues are sent back to the model for one regeneration."""
    issues: list[str] = []
    feature_ids = {f.id for f in brief.features}
    valid = []
    for d in drafts:
        if d.requirement_ref not in feature_ids:
            issues.append(f"test '{d.description}' refers to '{d.requirement_ref}', which is not a feature in the brief")
            continue
        if not d.ears.upper().startswith("WHEN") or "SHALL" not in d.ears.upper():
            issues.append(f"test '{d.description}' does not use the form 'WHEN ... THE SYSTEM SHALL ...'")
            continue
        valid.append(d)

    must = [f.id for f in brief.features if f.priority == "must"]
    for fid in must:
        if not any(d.requirement_ref == fid and d.kind == "happy_path" for d in valid):
            issues.append(f"no happy_path test for must-have feature '{fid}'")
    for fid in feature_ids & FORM_FEATURES:
        if not any(d.requirement_ref == fid and d.kind == "negative" for d in valid):
            issues.append(f"no negative test for form feature '{fid}'")

    # Keep coverage first when trimming to the limit: one happy path per must, one negative per form.
    chosen: list[GeneratedTest] = []
    for fid in must:
        chosen += [d for d in valid if d.requirement_ref == fid and d.kind == "happy_path"][:1]
    for fid in sorted(feature_ids & FORM_FEATURES):
        chosen += [d for d in valid if d.requirement_ref == fid and d.kind == "negative"][:1]
    chosen += [d for d in valid if d not in chosen]
    chosen = chosen[:limits.max_test_cases]

    tests = [
        AcceptanceTest(test_id=f"T{n:02d}", **d.model_dump())
        for n, d in enumerate(chosen, start=1)
    ]
    return tests, issues
