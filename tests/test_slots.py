"""Slot checklist, gaps and question policy (v6 Sections 6 and 8, D-102, D-104, D-112). No model calls."""
from agents.catalogue import load_catalogue
from agents.clarification import grounding, slots
from agents.clarification.schemas import UserAnswer
from agents.state import ClarificationState, Limits, Question, RequestedItem

CAT = load_catalogue()
LIMITS = Limits()


def state(**kwargs) -> ClarificationState:
    return ClarificationState(slots=slots.init_slots(), **kwargs)


def answered(c: ClarificationState, name: str, values: list[str]) -> None:
    s = slots.get_slot(c, name)
    s.status, s.values, s.source = "answered", values, "user_stated"


def ask(c: ClarificationState) -> Question:
    action, q = slots.select_next(c, CAT, LIMITS)
    assert action == "ask"
    c.questions.append(q)
    return q


def test_empty_request_asks_purpose_first_without_you_decide():
    c = state()
    gaps = slots.open_gaps(c, CAT, LIMITS)
    assert [g.key for g in gaps] == ["purpose", "visitor_actions"]
    q = ask(c)
    assert q.kind == "A" and not q.allow_you_decide
    assert {o.option_id for o in q.options} == {b.baseline_id for b in CAT.baselines}


def test_clear_request_asks_nothing():
    c = state()
    answered(c, "purpose", ["bakery"])
    grounding.add_match(c, CAT, "order-request", "user_stated")
    slots.fill_slots_from_items(c)
    assert slots.select_next(c, CAT, LIMITS) == ("draft", None)


def test_visitor_question_is_multi_select_with_recommendation():
    c = state()
    answered(c, "purpose", ["bakery"])
    grounding.add_match(c, CAT, "menu-catalog", "user_stated")
    q = ask(c)
    assert q.kind == "B" and q.multi_select and q.allow_you_decide
    assert [o.option_id for o in q.options if o.recommended] == ["order-request"]   # catalog baseline


def test_blocking_gap_is_never_defaulted_when_questions_run_out():
    c = state(questions_used=LIMITS.max_questions)
    action, missing = slots.select_next(c, CAT, LIMITS)
    assert action == "fail"
    assert "what the website is for" in missing


def test_same_slot_is_asked_at_most_twice():
    c = state()
    ask(c), ask(c)
    action, _ = slots.select_next(c, CAT, LIMITS)
    assert action == "fail"


def test_answer_validation():
    q = Question(question_id="q1", number=1, kind="B", slot="visitor_actions", text="?", multi_select=True,
                 options=[], allow_you_decide=True)
    q.options = slots.build_question(slots.Gap("B", "visitor_actions", ""), state(), CAT, LIMITS).options
    assert slots.validate_answer(q, UserAnswer(question_id="q1", kind="option", option_ids=["booking"])) is None
    assert slots.validate_answer(q, UserAnswer(question_id="q9", kind="option", option_ids=["booking"]))
    assert slots.validate_answer(q, UserAnswer(question_id="q1", kind="option", option_ids=["hack"]))
    assert slots.validate_answer(q, UserAnswer(question_id="q1", kind="other", text="x"))   # free text off


def test_you_decide_is_logged_as_an_assumption():
    c = state(baseline_hint="catalog")
    answered(c, "purpose", ["shop"])
    q = ask(c)
    slots.apply_you_decide(c, q, CAT)
    actions = slots.get_slot(c, "visitor_actions")
    assert actions.status == "answered" and actions.source == "user_delegated"
    assert actions.values == ["order-request"]
    assert c.assumptions and c.assumptions[0].default_applied == "order-request"


def test_core_unsupported_item_asks_and_no_means_out_of_scope():
    c = state(requested_items=[RequestedItem(item_id="i1", text="online store with card payments",
                                             candidate_capability_id="online-payments", is_core=True)])
    grounding.ground_items(c, CAT)
    answered(c, "purpose", ["shop"])
    q = ask(c)
    assert q.kind == "D"
    slots.apply_option_answer(c, q, ["no"], CAT)
    assert c.out_of_scope is not None


def test_core_unsupported_item_yes_adds_the_alternative():
    c = state(requested_items=[RequestedItem(item_id="i1", text="card payments",
                                             candidate_capability_id="online-payments", is_core=True)])
    grounding.ground_items(c, CAT)
    answered(c, "purpose", ["shop"])
    q = ask(c)
    slots.apply_option_answer(c, q, ["yes"], CAT)
    assert c.requested_items[0].alternative_accepted
    assert c.matches and c.matches[0].feature_id == CAT.capabilities["online-payments"].alternative_feature_ids[0]


def test_too_many_custom_features_lets_the_user_choose():
    c = state(requested_items=[RequestedItem(item_id=f"i{n}", text=f"special tool {n}") for n in range(7)])
    grounding.ground_items(c, CAT)
    answered(c, "purpose", ["studio"])
    answered(c, "visitor_actions", ["contact-form"])
    q = ask(c)
    assert q.slot == "custom_limit" and q.max_selections == LIMITS.max_custom_features
    keep = [o.option_id for o in q.options][:5]
    slots.apply_option_answer(c, q, keep, CAT)
    assert len(grounding.custom_items(c)) == 5
    assert sum(1 for i in c.requested_items if i.resolved_to == "limit") == 2
