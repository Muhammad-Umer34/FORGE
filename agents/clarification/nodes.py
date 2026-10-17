# D:\FYP\FORGE-1\agents\clarification\nodes.py
"""
Clarification Agent nodes (v6 Section 7). Each node is thin: it copies its state slice, calls the
modules that hold the rules (grounding, slots, brief, acceptance) or the LLM gateway, and returns
the updated slices. Nodes never write to the database (D-133).

Interrupt nodes (ask_user, await_confirmation) do nothing with side effects before interrupt(),
because LangGraph re-runs a node from its first line when the run resumes (D-122).
"""
from datetime import datetime, timezone
from typing import Any

from langgraph.types import interrupt

from agents.catalogue import Catalogue, load_catalogue
from agents.clarification import acceptance, grounding, prompts, slots
from agents.clarification import brief as briefs
from agents.clarification.schemas import (
    NO_VISITOR_ACTION, AnswerInterpretation, BriefReview, ConfirmationDecision, EditInterpretation,
    IntakeOutput, GeneratedTests, UserAnswer,
)
from agents.gateway import CallUsage, InvalidOutputError, ModelCallError, call_structured
from agents.state import (
    BriefCheck, ClarificationState, ClarifiedBrief, FailureInfo, GraphState, Limits, OutOfScopeInfo,
    UsageSummary, can_freeze, sum_usage,
)

TASK = "clarification"

FAILURE_MESSAGES = {   # D-121: three categories, three different messages
    "understanding": "We couldn't understand the request. Please describe your website in a sentence or two.",
    "missing_info": "We still need a few details before we can build your website.",
    "system": "FORGE had a technical problem. Your request was fine. Please try again in a few minutes.",
}
NOT_A_WEBSITE = "FORGE builds small-to-medium websites. This request isn't for a website."


# ---------------------------------------------------------------- helpers
def _ctx(state: GraphState) -> tuple[ClarificationState, Limits, Catalogue]:
    return state["clarification"].model_copy(deep=True), state["run_config"].limits, load_catalogue()


def _fail(c: ClarificationState, node: str, category: str, detail: str | None = None,
          missing: list[str] | None = None) -> ClarificationState:
    message = FAILURE_MESSAGES[category]
    if missing:
        message += " Please start again and include: " + "; ".join(missing) + "."
    c.failure = FailureInfo(node=node, category=category, message=message, detail=detail,
                            missing=missing or [], at=datetime.now(timezone.utc))
    c.status = "failed"
    return c


def _call(c: ClarificationState, schema, system: str, user: str) -> tuple[Any, UsageSummary]:
    """One gateway call; counts it against the budget even when it fails."""
    usage = CallUsage()
    try:
        result, usage = call_structured(TASK, schema, system, user)
        return result, _summary(usage)
    finally:
        c.calls_used += max(usage.calls, 1)


def _summary(u: CallUsage) -> UsageSummary:
    return UsageSummary(calls=u.calls, prompt_tokens=u.prompt_tokens, completion_tokens=u.completion_tokens,
                        unknown_token_calls=u.unknown_token_calls, total_latency_ms=u.latency_ms)


def _prompt(state: GraphState) -> str:
    return prompts.sanitise(state["request"].prompt, prompts.MAX_PROMPT_CHARS)[0]


def _pending_question(c: ClarificationState):
    return next(q for q in c.questions if q.question_id == c.pending_question_id)


def question_payload(q, max_questions: int) -> dict:
    """What the client sees for a question (v6 Section 4)."""
    return {
        "type": "question",
        "question_id": q.question_id, "number": q.number, "max_questions": max_questions,
        "kind": q.kind, "slot": q.slot, "text": q.text,
        "options": [o.model_dump() for o in q.options],
        "multi_select": q.multi_select, "max_selections": q.max_selections,
        "allow_you_decide": q.allow_you_decide, "allow_other_text": q.allow_other_text,
    }


def confirmation_view(state: GraphState) -> dict:
    c, limits = state["clarification"], state["run_config"].limits
    return briefs.confirmation_payload(state["brief"], c, limits, edit_allowed=slots.free_text_allowed(c, limits))


# ---------------------------------------------------------------- N0 - N2
def load_resources(state: GraphState) -> dict:
    c = state["clarification"].model_copy(deep=True)
    try:
        load_catalogue()
    except Exception as error:   # missing or inconsistent data files
        return {"clarification": _fail(c, "load_resources", "system", str(error))}
    if not c.slots:
        c.slots = slots.init_slots()
    c.status = "analysing"
    return {"clarification": c}


def sanitise_input(state: GraphState) -> dict:
    c = state["clarification"].model_copy(deep=True)
    _, flags = prompts.sanitise(state["request"].prompt, prompts.MAX_PROMPT_CHARS)
    c.input_flags += [f for f in flags if f not in c.input_flags]
    return {"clarification": c}


def intake(state: GraphState) -> dict:
    c, limits, cat = _ctx(state)
    text = _prompt(state)
    try:
        out, usage = _call(c, IntakeOutput, prompts.INTAKE_SYSTEM,
                           prompts.intake_user(text, cat.feature_summary(), cat.unsupported_summary()))
    except InvalidOutputError as error:
        return {"clarification": _fail(c, "intake", "understanding", str(error))}
    except ModelCallError as error:
        return {"clarification": _fail(c, "intake", "system", str(error))}

    c.is_website_request = out.is_website_request
    if not out.is_website_request:           # N3: request-level scope (D-108)
        c.out_of_scope = OutOfScopeInfo(reason=NOT_A_WEBSITE)
        c.status = "out_of_scope"
        return {"clarification": c, "usage": usage}

    c.detected_language, c.romanized = out.detected_language, out.romanized
    c.is_business, c.business_type, c.goal, c.style_hint = out.is_business, out.business_type, out.goal, out.style_hint
    if out.purpose_known and (out.business_type or out.goal):
        purpose = slots.get_slot(c, "purpose")
        purpose.status, purpose.values, purpose.source = "answered", [out.business_type or out.goal], "user_stated"
    if out.no_visitor_actions:
        actions = slots.get_slot(c, "visitor_actions")
        actions.status, actions.values, actions.source = "answered", [NO_VISITOR_ACTION], "user_stated"
    dropped = grounding.items_from_model(c, out.items, text)
    c.input_flags += dropped
    if dropped:
        c.risk_flags.append("dropped_unverified_item")
    return {"clarification": c, "usage": usage}


# ---------------------------------------------------------------- N4 - N8
def ground_items(state: GraphState) -> dict:
    c, _, cat = _ctx(state)
    grounding.ground_items(c, cat)
    slots.fill_slots_from_items(c)
    c.status = "analysing"
    return {"clarification": c}


def select_question(state: GraphState) -> dict:
    c, limits, cat = _ctx(state)
    action, value = slots.select_next(c, cat, limits)
    if action == "ask":
        c.questions.append(value)
        c.pending_question_id = value.question_id
        c.status = "awaiting_answer"
    elif action == "draft":
        c.status = "drafting"
    else:
        _fail(c, "select_question", "missing_info", missing=value)
    return {"clarification": c}


def ask_user(state: GraphState) -> dict:
    """Interrupt only (N7)."""
    c = state["clarification"]
    payload = question_payload(_pending_question(c), state["run_config"].limits.max_questions)
    raw = interrupt(payload, response_schema=UserAnswer)
    answer = UserAnswer.model_validate(raw if isinstance(raw, dict) else raw.model_dump())
    c = c.model_copy(deep=True)
    q = _pending_question(c)
    q.answer_kind, q.answer_option_ids = answer.kind, answer.option_ids
    if answer.text:
        q.answer_text = prompts.sanitise(answer.text, prompts.MAX_ANSWER_CHARS)[0]
    return {"clarification": c}


def interpret_answer(state: GraphState) -> dict:
    c, limits, cat = _ctx(state)
    q = _pending_question(c)
    answer = UserAnswer(question_id=q.question_id, kind=q.answer_kind or "other",
                        option_ids=q.answer_option_ids, text=q.answer_text)
    c.questions_used += 1
    c.pending_question_id = None
    c.status = "analysing"
    update: dict = {"clarification": c}

    if slots.validate_answer(q, answer):
        return update                       # not usable: the same gap is asked again (counts as a question)
    if answer.kind == "option":
        slots.apply_option_answer(c, q, answer.option_ids, cat)
    elif answer.kind == "you_decide":
        slots.apply_you_decide(c, q, cat)
    else:
        if not slots.free_text_allowed(c, limits):
            return update
        flags = prompts.sanitise(answer.text or "", prompts.MAX_ANSWER_CHARS)[1]
        c.input_flags += [f for f in flags if f not in c.input_flags]
        c.risk_flags.append("free_text_answer")
        options = [o.model_dump(include={"option_id", "label"}) for o in q.options]
        try:
            out, usage = _call(c, AnswerInterpretation, prompts.ANSWER_SYSTEM,
                               prompts.answer_user(q.text, options, answer.text or "", cat.feature_summary()))
        except ModelCallError as error:     # includes InvalidOutputError
            return {"clarification": _fail(c, "interpret_answer", "system", str(error))}
        update["usage"] = usage
        if out.understood:
            allowed = [o for o in out.option_ids if o in {opt.option_id for opt in q.options}]
            if q.kind == "A" and (out.business_type or out.goal):
                c.business_type, c.goal = out.business_type or c.business_type, out.goal or c.goal
                if out.is_business is not None:
                    c.is_business = out.is_business
                purpose = slots.get_slot(c, "purpose")
                purpose.status, purpose.values, purpose.source = "answered", [c.business_type or c.goal], "user_confirmed"
            elif allowed:
                slots.apply_option_answer(c, q, allowed if q.multi_select else allowed[:1], cat)
            if out.new_items:
                c.input_flags += grounding.items_from_model(c, out.new_items, answer.text or "")

    if c.out_of_scope:
        c.status = "out_of_scope"
    return update


# ---------------------------------------------------------------- N9 - N11
def draft_brief(state: GraphState) -> dict:
    c, limits, cat = _ctx(state)
    grounding.propose_extras(c, cat, limits)
    previous = state.get("brief")
    brief = briefs.draft_brief(c, cat, version=previous.version if previous else 1)
    c.status = "checking"
    return {"clarification": c, "brief": brief}


def check_brief(state: GraphState) -> dict:
    c, limits, cat = _ctx(state)
    brief = state["brief"]
    issues = briefs.code_checks(brief, c, cat, limits)
    update: dict = {"clarification": c}

    review_notes: list[str] = []
    reviewed = c.check.reviewed_by_model if c.check else False
    if not issues and c.risk_flags and not reviewed and slots.free_text_allowed(c, limits):
        answers = [q.answer_text or ", ".join(q.answer_option_ids) for q in c.questions if q.answer_kind]
        try:   # optional call (D-126): a failure only skips the review
            out, usage = _call(c, BriefReview, prompts.REVIEW_SYSTEM,
                               prompts.review_user(_prompt(state), answers, briefs.brief_view_for_model(brief)))
            update["usage"] = usage
            reviewed = True
            # Only features read from the request itself can be "invented"; the user chose, delegated or saw the rest (D-148).
            stated = {f.id: f.name for f in brief.features if f.source == "user_stated"}
            review_notes += [f'We added "{stated[i]}". Remove it with Edit if you did not want it.'
                             for i in out.invented_feature_ids if i in stated]
            review_notes += [f'We may not have covered: "{m}". Use Edit to add it.' for m in out.missed_requests]
        except ModelCallError:
            pass

    c.check = BriefCheck(passed=not issues, issues=issues or review_notes, reviewed_by_model=reviewed,
                         repaired=c.repairs_used > 0)
    if issues and c.repairs_used >= limits.max_repairs:
        _fail(c, "check_brief", "system", "brief failed code checks: " + "; ".join(issues))
    return update


def repair(state: GraphState) -> dict:
    c = state["clarification"].model_copy(deep=True)
    c.repairs_used += 1
    return {"clarification": c, "brief": briefs.repair(state["brief"].model_copy(deep=True), c)}


# ---------------------------------------------------------------- N12 - N14
def build_confirmation(state: GraphState) -> dict:
    c = state["clarification"].model_copy(deep=True)
    c.confirmation.shown = True
    c.confirmation.limits_notice_shown = bool(state["brief"].unsupported)
    c.confirmation.decision = None
    c.status = "awaiting_confirmation"
    return {"clarification": c}


def await_confirmation(state: GraphState) -> dict:
    """Interrupt only (N13). The decision is stored; apply_confirmation acts on it."""
    raw = interrupt(confirmation_view(state), response_schema=ConfirmationDecision)
    decision = ConfirmationDecision.model_validate(raw if isinstance(raw, dict) else raw.model_dump())
    c = state["clarification"].model_copy(deep=True)
    c.confirmation.decision = decision.decision
    if decision.decision == "edit":
        c.pending_edit_text = prompts.sanitise(decision.edit_text or "", prompts.MAX_ANSWER_CHARS)[0]
    elif decision.decision == "confirm":
        pending = {e.feature_id for e in c.proposed_extras if e.status == "pending"}
        c.confirmation.ticked_feature_ids = [f for f in decision.ticked_extra_ids if f in pending]
        defaults = {f.id for f in state["brief"].features if f.source == "baseline_default"}
        c.removed_feature_ids += [f for f in decision.unticked_default_ids if f in defaults]
        if decision.style in slots.STYLE_THEMES:
            style = slots.get_slot(c, "style")
            style.status, style.values, style.source = "answered", [decision.style], "user_confirmed"
    return {"clarification": c}


def apply_confirmation(state: GraphState) -> dict:
    c, limits, cat = _ctx(state)
    decision = c.confirmation.decision

    if decision == "cancel":
        c.status = "cancelled"
        return {"clarification": c}

    if decision == "edit":
        update: dict = {"clarification": c}
        text = c.pending_edit_text or ""
        c.pending_edit_text = None
        if not text or c.confirmation.edits_used >= limits.max_confirmation_edits or not slots.free_text_allowed(c, limits):
            return update                    # edit not possible: show the confirmation screen again
        c.confirmation.edits_used += 1
        flags = prompts.sanitise(text, prompts.MAX_ANSWER_CHARS)[1]
        c.input_flags += [f for f in flags if f not in c.input_flags]
        c.risk_flags.append("free_text_edit")
        current = [{"id": f.id, "name": f.name} for f in state["brief"].features]
        try:
            out, usage = _call(c, EditInterpretation, prompts.EDIT_SYSTEM,
                               prompts.edit_user(current, text, cat.feature_summary()))
        except ModelCallError as error:
            return {"clarification": _fail(c, "apply_confirmation", "system", str(error))}
        update["usage"] = usage
        if out.understood:
            brief_ids = {f.id for f in state["brief"].features}
            for fid in out.remove_feature_ids:
                if fid in brief_ids and fid not in c.removed_feature_ids:
                    c.removed_feature_ids.append(fid)
                    for item in c.requested_items:
                        if item.resolved_to == fid:
                            item.resolution = "dropped_by_user"
                            grounding.remove_item_matches(c, item.item_id)
            c.input_flags += grounding.items_from_model(c, out.add_items, text)
            if out.style_hint:
                c.style_hint = out.style_hint
        c.check = None                       # the brief changes: check it again, including the review
        c.status = "analysing"
        return update

    # confirm: ticked extras join the brief, the rest are rejected; then redraft and re-run the code checks
    for extra in c.proposed_extras:
        if extra.status == "pending":
            extra.status = "accepted" if extra.feature_id in c.confirmation.ticked_feature_ids else "rejected"
    brief = briefs.draft_brief(c, cat, version=state["brief"].version)
    issues = briefs.code_checks(brief, c, cat, limits)
    if issues:
        return {"clarification": _fail(c, "apply_confirmation", "system", "; ".join(issues))}
    c.status = "generating_tests"
    return {"clarification": c, "brief": brief}


# ---------------------------------------------------------------- N15 - N17
def generate_tests(state: GraphState) -> dict:
    c, limits, _ = _ctx(state)
    brief: ClarifiedBrief = state["brief"].model_copy(deep=True)
    view = briefs.brief_view_for_model(brief)
    total = UsageSummary()
    issues: list[str] | None = None

    for attempt in range(2):                 # first try + one regeneration with the issues listed
        if attempt and c.calls_used >= limits.call_hard_cap:
            break
        try:
            out, usage = _call(c, GeneratedTests, prompts.TESTS_SYSTEM,
                               prompts.tests_user(view, limits.max_test_cases, issues))
        except ModelCallError as error:
            return {"clarification": _fail(c, "generate_tests", "system", str(error)), "usage": total}
        total = sum_usage(total, usage)
        tests, issues = acceptance.validate_tests(out.tests, brief, limits)
        if not issues:
            break

    coverage = [i for i in issues or [] if i.startswith("no ")]
    if coverage:
        return {"clarification": _fail(c, "generate_tests", "system", "; ".join(coverage)), "usage": total}
    brief.test_cases = tests
    return {"clarification": c, "brief": brief, "usage": total}


def freeze(state: GraphState) -> dict:
    c = state["clarification"].model_copy(deep=True)
    brief = state["brief"].model_copy(deep=True)
    ok, reasons = can_freeze({**state, "clarification": c, "brief": brief})
    if not ok:
        return {"clarification": _fail(c, "freeze", "system", "; ".join(reasons))}
    brief.status = "ready"
    brief.frozen_at = datetime.now(timezone.utc)
    c.status = "done"
    return {"clarification": c, "brief": brief}
