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
    message_kind="website_request", detected_language="en", romanized=False, purpose_known=True, is_business=True,
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

    themes = screen["themes"]
    assert len(themes) == 3 and sum(1 for th in themes if th["id"] == screen["theme_selected"]) == 1
    picked = next(th for th in themes if th["id"] != screen["theme_selected"])            # choose a non-default theme
    result = graph.invoke(Command(resume={"decision": "confirm", "theme_id": picked["id"]}), config)
    assert pending(result) is None
    assert result["clarification"].status == "done"
    assert result["brief"].status == "ready" and result["brief"].test_cases                  # TC-11
    theme = result["brief"].theme
    assert theme["theme_id"] == picked["id"] and theme["contrast"]["standard"] == "WCAG 2.2 AA"   # D-159
    assert set(theme["tokens"]) == {"light", "dark"} and "primary-foreground" in theme["tokens"]["light"]
    assert result["control"].stage == Stage.RETRIEVING
    assert result["usage"].calls == 2                                          # intake + tests


def not_a_request(kind: str) -> IntakeOutput:
    return IntakeOutput(message_kind=kind, detected_language="en", romanized=False, purpose_known=False, is_business=False)


@pytest.mark.parametrize("prompt, kind, words", [
    ("write my CV text", "off_topic", "only help with building websites"),             # TC-06
    ("what is the derivative of x squared", "off_topic", "can't answer that"),         # TC-13
    ("what can you build? can you take payments?", "about_forge", "can't take online payments"),  # TC-14
    ("asdf qwer zxcv", "unclear", "couldn't tell what you need"),
])
def test_messages_that_are_not_requests_get_a_reply(graph, monkeypatch, prompt, kind, words):
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: not_a_request(kind)}))
    result, _ = start(graph, prompt)
    c = result["clarification"]
    assert pending(result) is None and not c.questions
    assert c.status == "replied" and c.reply.kind == kind and words in c.reply.message
    assert result["control"].stage == Stage.REPLIED and not result["control"].failed


def test_greeting_is_answered_without_a_model_call(graph, monkeypatch):          # TC-12, D-151
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: ModelCallError("must not be called")}))
    result, _ = start(graph, "Hi how are you ?")
    c = result["clarification"]
    assert c.status == "replied" and c.reply.kind == "greeting"
    assert c.reply.message.startswith("I'm doing well")
    assert c.calls_used == 0 and result["usage"].calls == 0


def test_greeting_with_a_request_starts_the_workflow(graph, monkeypatch):          # TC-15
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: BAKERY_INTAKE, BriefReview: BriefReview()}))
    result, _ = start(graph, "Hi! I need a website for my bakery with our menu")
    assert pending(result)["type"] == "question"
    assert result.get("clarification") is None or result["clarification"].status != "replied"


def test_provider_failure_pauses_the_run_and_it_continues_later(graph, monkeypatch):     # TC-08, persistence
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: ModelCallError("503 UNAVAILABLE")}))
    rid = f"req_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": rid}}
    state = initial_state(RequestInfo(request_id=rid, user_id="test", project_id="test", prompt="a bakery website",
                                      created_at=datetime.now(timezone.utc)))
    with pytest.raises(ModelCallError):
        graph.invoke(state, config)
    paused = graph.get_state(config)
    assert paused.values and paused.next and not paused.interrupts       # stopped mid-way, progress kept
    assert paused.values["clarification"].failure is None                 # not ended as "failed"

    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: BAKERY_INTAKE, BriefReview: BriefReview()}))
    assert pending(graph.invoke(None, config))["type"] == "question"      # the same run continues


def test_declining_the_alternative_ends_out_of_scope(graph, monkeypatch):
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: IntakeOutput(
        message_kind="website_request", detected_language="en", romanized=False, purpose_known=True, is_business=True,
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
        IntakeOutput: IntakeOutput(message_kind="website_request", detected_language="en", romanized=False,
                                   purpose_known=False, is_business=True),
        AnswerInterpretation: AnswerInterpretation(understood=False),
    }))
    result, config = start(graph, "build me a website")
    reasks = []
    for _ in range(3):
        q = pending(result)
        if q is None:
            break
        reasks.append(q["reask"])
        result = graph.invoke(Command(resume={"question_id": q["question_id"], "kind": "other", "text": "dunno"}), config)
    assert reasks == [False, True]                                                # D-153 notice on the second ask
    failure = result["clarification"].failure
    assert failure.category == "missing_info" and "what the website is for" in failure.missing   # TC-05


def test_review_never_flags_what_the_user_delegated(graph, monkeypatch):     # D-148, D-149
    monkeypatch.setattr(nodes, "call_structured", fake_model({
        IntakeOutput: IntakeOutput(message_kind="website_request", detected_language="en", romanized=False,
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


def test_hex_in_the_request_preselects_the_brand_theme(graph, monkeypatch):     # D-157, D-158
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: BAKERY_INTAKE.model_copy(
        update={"no_visitor_actions": True})}))                     # the model misses the colour; code reads it
    result, _ = start(graph, "a website for my bakery with our menu, brand colour #1A7F5A")
    screen = pending(result)
    selected = next(th for th in screen["themes"] if th["id"] == screen["theme_selected"])
    assert selected["kind"] == "brand" and selected["label"] == "Your colour #1a7f5a"


def _to_confirmation(graph, monkeypatch, prompt="a website for my bakery with our menu", reader=None):
    monkeypatch.setattr(nodes, "call_structured", fake_model({IntakeOutput: BAKERY_INTAKE.model_copy(
        update={"no_visitor_actions": True})}))
    if reader:
        monkeypatch.setattr(nodes.reference_style, "read_reference", reader)
    result, config = start(graph, prompt)
    assert pending(result)["type"] == "confirmation"
    return result, config


def test_logo_colour_becomes_the_selected_theme(graph, monkeypatch):                # D-163
    result, config = _to_confirmation(graph, monkeypatch)
    assert "theme_source" in pending(result)["actions"]
    result = graph.invoke(Command(resume={"decision": "theme_source",
                                          "theme_source": {"kind": "logo", "colour": "#2156AA"}}), config)
    screen = pending(result)
    chosen = next(th for th in screen["themes"] if th["id"] == screen["theme_selected"])
    assert chosen["kind"] == "logo" and chosen["label"] == "Your logo colour"
    assert screen["theme_sources_left"]["logo"] == 2                                   # D-169: 3 tries per source


def test_website_in_the_request_is_read_once_and_not_built(graph, monkeypatch):      # D-165
    calls = []
    def reader(url):
        calls.append(url)
        return {"url": "https://www.example.com", "host": "example.com", "primary": "#ff385c", "is_dark": True,
                "radius": "1rem", "font_pair_id": "inter", "personality": "playful", "notes": []}
    result, _ = _to_confirmation(graph, monkeypatch, "a website for my bakery with our menu, make it look like www.example.com", reader)
    screen = pending(result)
    chosen = next(th for th in screen["themes"] if th["id"] == screen["theme_selected"])
    assert calls == ["www.example.com"] and chosen["label"] == "Inspired by example.com" and chosen["default_mode"] == "dark"
    assert all("example" not in f["name"].lower() for f in screen["features"])          # the link is not a feature


def test_unreadable_website_gives_a_notice_not_a_failure(graph, monkeypatch):
    def reader(url):
        raise nodes.reference_style.ReferenceSiteError("We couldn't open that website.")
    result, config = _to_confirmation(graph, monkeypatch, reader=reader)
    result = graph.invoke(Command(resume={"decision": "theme_source",
                                          "theme_source": {"kind": "website", "url": "blocked-site.com"}}), config)
    screen = pending(result)
    assert screen["type"] == "confirmation" and "upload a screenshot" in screen["theme_notice"]


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
    assert result["clarification"].status == "replied"                        # TC-06
    assert result["clarification"].reply.kind == "off_topic"


@live
def test_live_maths_question_is_declined(graph):
    result, _ = start(graph, "What is 15% of 240?")
    c = result["clarification"]
    assert c.status == "replied" and c.reply.kind == "off_topic"             # TC-13
