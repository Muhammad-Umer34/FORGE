"""
End-to-end runs of the Clarification Agent through the Orchestrator graph, including the pauses.

Offline tests (default) replace the model with fixed answers, so they cost nothing and show the
graph wiring, interrupts and end states work. Live tests call Gemini through the real gateway and
run only when FORGE_LIVE_TESTS=1 is set (they use API credits):

    FORGE_LIVE_TESTS=1 .venv/Scripts/python.exe -m pytest tests/test_clarification_flow.py -k live -s
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

from agents.clarification import nodes
from agents.clarification.schemas import (
    AnswerInterpretation, BriefReview, GeneratedTest, GeneratedTests, IntakeItem, IntakeOutput,
)
from agents.gateway import CallUsage, ModelCallError
from agents.orchestrator import build_forge_graph
from agents.state import RequestInfo, Stage, initial_state, msgpack_allowlist


def start(graph, prompt: str):
    rid = f"req_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": rid}}
    state = initial_state(RequestInfo(request_id=rid, user_id="test", project_id="test", prompt=prompt,
                                      created_at=datetime.now(timezone.utc)))
    return graph.invoke(state, config), config


def pending(result) -> dict | None:
    interrupts = result.get("__interrupt__") or []
    return interrupts[0].value if interrupts else None


# ---------------------------------------------------------------- offline (fake model)
def fake_model(responses: dict):
    def call(task, schema, system, user):
        value = responses[schema]
        if isinstance(value, Exception):
            raise value
        return (value(user) if callable(value) else value), CallUsage(calls=1, prompt_tokens=10, completion_tokens=5)
    return call


def bakery_tests(_user):
    return GeneratedTests(tests=[
        GeneratedTest(requirement_ref=ref, kind=kind, ears="WHEN a visitor uses it THE SYSTEM SHALL work",
                      given="g", when="w", then="t", check="element_present", description=f"{ref} {kind}",
                      expected_result="ok")
        for ref, kind in [("menu-catalog", "happy_path"), ("order-request", "happy_path"),
                          ("order-request", "negative"), ("contact-info", "happy_path")]
    ])


BAKERY_INTAKE = IntakeOutput(
    is_website_request=True, detected_language="en", romanized=False, purpose_known=True, is_business=True,
    business_type="bakery", goal="Show the menu", items=[
        IntakeItem(text="our menu", kind="feature", evidence="our menu", candidate_feature_id="menu-catalog")],
)


@pytest.fixture
def graph():
    # Same serializer settings as the API, so unregistered state types would show up here.
    serde = JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist())
    return build_forge_graph().compile(checkpointer=InMemorySaver(serde=serde))


def test_vague_request_asks_then_confirms_then_freezes(graph, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake_model({
        IntakeOutput: BAKERY_INTAKE, GeneratedTests: bakery_tests,
        BriefReview: BriefReview(),
    }))
    result, config = start(graph, "a website for my bakery with our menu")
    q = pending(result)
    assert q["type"] == "question" and q["kind"] == "B"                       # TC-02

    result = graph.invoke(Command(resume={"question_id": q["question_id"], "kind": "option",
                                          "option_ids": ["order-request"]}), config)
    screen = pending(result)
    assert screen["type"] == "confirmation" and "send an order request" in screen["summary"]   # TC-03

    result = graph.invoke(Command(resume={"decision": "confirm", "style": "warm"}), config)
    assert pending(result) is None
    assert result["clarification"].status == "done"
    assert result["brief"].status == "ready" and result["brief"].test_cases                  # TC-11
    assert result["brief"].style == {"theme": "warm"}
    assert result["control"].stage == Stage.RETRIEVING
    assert result["usage"].calls == 2                                          # intake + tests


def test_not_a_website_is_out_of_scope_without_questions(graph, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: IntakeOutput(
        is_website_request=False, detected_language="en", romanized=False, purpose_known=False, is_business=False)}))
    result, _ = start(graph, "write my CV text")
    assert pending(result) is None
    assert result["clarification"].status == "out_of_scope"                   # TC-06
    assert result["control"].stage == Stage.OUT_OF_SCOPE


def test_provider_failure_says_the_request_was_fine(graph, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: ModelCallError("503 UNAVAILABLE")}))
    result, _ = start(graph, "a bakery website")
    failure = result["clarification"].failure
    assert failure.category == "system" and "Your request was fine" in failure.message          # TC-08
    assert result["control"].failed and result["control"].failure_reason == failure.message


def test_declining_the_alternative_ends_out_of_scope(graph, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: IntakeOutput(
        is_website_request=True, detected_language="en", romanized=False, purpose_known=True, is_business=True,
        business_type="clothing shop", items=[IntakeItem(
            text="online store with card payments", kind="feature", evidence="online store with card payments",
            candidate_capability_id="online-payments", is_core=True)])}))
    result, config = start(graph, "an online store with card payments for my clothing shop")
    q = pending(result)
    assert q["kind"] == "D"
    result = graph.invoke(Command(resume={"question_id": q["question_id"], "kind": "option", "option_ids": ["no"]}), config)
    assert result["clarification"].status == "out_of_scope"                   # TC-04


def test_unhelpful_answers_fail_with_missing_info(graph, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake_model({
        IntakeOutput: IntakeOutput(is_website_request=True, detected_language="en", romanized=False,
                                   purpose_known=False, is_business=True),
        AnswerInterpretation: AnswerInterpretation(understood=False),
    }))
    result, config = start(graph, "build me a website")
    for _ in range(3):
        q = pending(result)
        if q is None:
            break
        result = graph.invoke(Command(resume={"question_id": q["question_id"], "kind": "other", "text": "dunno"}), config)
    failure = result["clarification"].failure
    assert failure.category == "missing_info" and "what the website is for" in failure.missing   # TC-05


def test_review_never_flags_what_the_user_delegated(graph, monkeypatch):     # D-148, D-149
    monkeypatch.setattr(nodes, "call_structured", fake_model({
        IntakeOutput: IntakeOutput(is_website_request=True, detected_language="en", romanized=False,
                                   purpose_known=False, is_business=True),
        # The model wrongly reports the delegated order form and the default product grid as invented.
        BriefReview: BriefReview(invented_feature_ids=["order-request", "product-grid"]),
    }))
    result, config = start(graph, "a website for my shop")
    q = pending(result)
    result = graph.invoke(Command(resume={"question_id": q["question_id"], "kind": "option", "option_ids": ["catalog"]}), config)
    q = pending(result)
    assert q["kind"] == "B"
    result = graph.invoke(Command(resume={"question_id": q["question_id"], "kind": "you_decide"}), config)
    screen = pending(result)
    assert screen["type"] == "confirmation"
    assert screen["please_check"] == []
    features = {f["id"]: f["source"] for f in screen["features"]}
    assert features["order-request"] == "user_delegated"
    assert features["product-grid"] == "baseline_default"


def test_cancel_at_confirmation(graph, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: BAKERY_INTAKE.model_copy(
        update={"no_visitor_actions": True})}))
    result, config = start(graph, "a website for my bakery with our menu")
    assert pending(result)["type"] == "confirmation"                          # TC-01: no question asked
    result = graph.invoke(Command(resume={"decision": "cancel"}), config)
    assert result["control"].stage == Stage.CANCELLED


# ---------------------------------------------------------------- live (real Gemini, costs credits)
live = pytest.mark.skipif(os.getenv("FORGE_LIVE_TESTS") != "1", reason="set FORGE_LIVE_TESTS=1 to call Gemini")


@live
def test_live_clear_request_goes_to_confirmation(graph):
    result, config = start(graph, "Bakery website: show our cake menu, let customers send pre-order requests, "
                                  "show opening hours and a map to the shop.")
    screen = pending(result)
    print("\n", screen)
    assert screen and screen["type"] == "confirmation"                        # TC-01
    result = graph.invoke(Command(resume={"decision": "confirm"}), config)
    c, brief = result["clarification"], result.get("brief")
    print(c.status, c.calls_used, [(t.requirement_ref, t.kind) for t in (brief.test_cases if brief else [])])
    assert c.status == "done" and brief.test_cases


@live
def test_live_vague_request_asks(graph):
    result, _ = start(graph, "a website for my shop")
    q = pending(result)
    print("\n", q)
    assert q and q["type"] == "question"                                      # TC-02


@live
def test_live_card_payments_store(graph):
    result, _ = start(graph, "I want an online store for my clothes where customers pay by card.")
    q = pending(result)
    print("\n", q)
    assert q and q["kind"] == "D"                                             # TC-04


@live
def test_live_not_a_website(graph):
    result, _ = start(graph, "Write a cover letter for a junior accountant job.")
    assert result["clarification"].status == "out_of_scope"                   # TC-06
