"""The fixed evaluation set (scripts/eval_briefs.json, D-217) stays valid: unique ids, real catalogue ids, and an
answer key the simulated owner can use. No model calls."""
import json
from pathlib import Path

import pytest

from agents.catalogue import load_catalogue
from agents.clarification.schemas import VISITOR_ACTION_FEATURES

BRIEFS = json.loads((Path(__file__).resolve().parents[1] / "scripts" / "eval_briefs.json").read_text(encoding="utf-8"))["briefs"]
CAT = load_catalogue()


def test_the_set_has_unique_ids_and_covers_every_group():
    ids = [b["id"] for b in BRIEFS]
    assert len(ids) == len(set(ids)) and 20 <= len(ids) <= 25
    assert len({b["group"] for b in BRIEFS}) == 8


@pytest.mark.parametrize("brief", BRIEFS, ids=lambda b: b["id"])
def test_every_brief_uses_real_ids(brief):
    assert brief["expect"] in ("planned", "out_of_scope", "failed")
    assert set(brief["must"]) <= set(CAT.features)
    assert set(brief["must_not"]) <= set(CAT.features) | set(CAT.capabilities)
    key = brief["answers"]
    assert key.get("purpose") in (None, *[b.baseline_id for b in CAT.baselines])
    assert set(key.get("visitor_actions", [])) <= set(VISITOR_ACTION_FEATURES)
    assert key.get("continue_without_unsupported", "yes") in ("yes", "no")
