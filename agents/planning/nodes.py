# D:\FYP\FORGE-1\agents\planning\nodes.py
"""
Planning Agent nodes (plan v2 §5). Each node is thin: it copies its slices, calls the modules that hold the
rules (fixed, assemble, checks, texts) or the LLM gateway, and returns the updated slices. Nodes never write
to the database.

await_plan_approval does nothing with side effects before interrupt(), because LangGraph re-runs a node from
its first line when the run resumes.
"""
from datetime import datetime, timezone
from typing import Any

from langgraph.types import interrupt

from agents.catalogue import load_catalogue
from agents.clarification.prompts import sanitise
from agents.gateway import SPENDING_LIMIT, SPENDING_LIMIT_MESSAGE, CallUsage, InvalidOutputError, call_structured
from agents.planning import assemble, checks, fixed, prompts, texts
from agents.planning.schemas import DataDesign, PlanDecision, PlanFix, SiteDesign, SiteTexts
from agents.state import BuildPlan, FailureInfo, GraphState, PlanningState, UsageSummary, budget_left

FAILURE_MESSAGE = "We could not finish planning your site. Please try again."
MAX_CHANGE_CHARS = 500


# ---------------------------------------------------------------- helpers
def _p(state: GraphState) -> PlanningState:
    return state["planning"].model_copy(deep=True)


def _fail(p: PlanningState, node: str, detail: str) -> PlanningState:
    """Planning runs on a confirmed brief, so a failure is always a system problem (plan v2 §10)."""
    message = SPENDING_LIMIT_MESSAGE if detail == SPENDING_LIMIT else FAILURE_MESSAGE
    p.failure = FailureInfo(node=node, category="system", message=message, detail=detail[:2000],
                            at=datetime.now(timezone.utc))
    p.status = "failed"
    return p


def _call(state: GraphState, p: PlanningState, task: str, schema, system: str, user: str) -> tuple[Any, UsageSummary]:
    """One gateway call, counted even when it fails. A model that cannot be reached raises ModelCallError, which
    stops the run before this step so it can be continued later; output wrong twice is handled by each step."""
    usage = CallUsage()
    try:
        result, usage = call_structured(task, schema, system, user, budget_left(state, p.spent_before_usd))
        return result, UsageSummary(calls=usage.calls, prompt_tokens=usage.prompt_tokens,
                                    completion_tokens=usage.completion_tokens,
                                    unknown_token_calls=usage.unknown_token_calls, total_latency_ms=usage.latency_ms,
                                    estimated_cost_usd=usage.cost_usd)
    finally:
        p.calls_used += max(usage.calls, 1)


def _brief_view(state: GraphState) -> dict:
    """The brief as the model sees it: no theme colours, no clarified text written for the user."""
    brief = state["brief"]
    view = brief.model_dump(mode="json", exclude={"theme", "clarified_text", "frozen_at", "status", "version"})
    view["features"] = [f for f in view["features"] if f["tier"] != "unsupported"]
    view["test_cases"] = [{"test_id": t.test_id, "feature": t.requirement_ref, "then": t.then} for t in brief.test_cases]
    return view


def _site(p: PlanningState) -> SiteDesign:
    return SiteDesign.model_validate(p.site_design)


def _data(p: PlanningState) -> DataDesign | None:
    return DataDesign.model_validate(p.data_design) if p.data_design else None


def _build(state: GraphState, p: PlanningState) -> BuildPlan:
    old = state.get("plan")
    return assemble.build_plan(state["brief"], state["retrieval"], _site(p), _data(p), load_catalogue(),
                               old.texts if old else None)


def plan_view(plan: BuildPlan, p: PlanningState, limits) -> dict:
    """The short plan summary the user approves (plan v2 step 8)."""
    cat = load_catalogue()
    specs = {s.spec_id: s.name for s in plan.custom_specs}
    names = {c.section_id: specs.get(c.custom_spec_id) if c.custom else
             cat.components[c.component_id].name if c.component_id in cat.components else c.section_id
             for c in plan.components}
    hero = next((t for t in plan.texts if t.slot_id == assemble.HERO_HEADLINE), None)
    return {
        "type": "plan_approval",
        "pages": [{"title": pg.title, "route": pg.route, "in_menu": pg.in_menu,
                   "sections": [names[s] for s in pg.section_ids]} for pg in plan.pages],
        "site_wide": [names[c.section_id] for c in plan.components if c.page == "all"],
        "hero_headline": hero.text if hero else "",
        "hero_alternatives": hero.alternatives if hero else [],
        "custom_parts": [{"name": s.name, "purpose": s.purpose} for s in plan.custom_specs],
        "stored": [{"title": v.title, "columns": v.columns, "statuses": v.statuses} for v in plan.dashboard_views],
        "details_needed": [f.label for f in plan.content_schema],
        "not_built": [n.model_dump() for n in plan.not_built],
        "assumptions": [a.text for a in plan.assumptions],
        "changes_left": max(limits.max_plan_edits - p.edits_used, 0),
        "notice": p.notice,
    }


# ---------------------------------------------------------------- steps 1-2
def check_input(state: GraphState) -> dict:
    p = _p(state)
    p.status = "drafting"
    problems = fixed.check_input(state.get("brief"), state.get("retrieval"), load_catalogue())
    return {"planning": _fail(p, "check_input", "; ".join(problems)) if problems else p}


# ---------------------------------------------------------------- steps 3-5
def design_site(state: GraphState) -> dict:
    p, cat, limits = _p(state), load_catalogue(), state["run_config"].limits
    brief, retrieval = state["brief"], state["retrieval"]
    opts = fixed.options(brief, retrieval, cat)
    user = prompts.site_user(_brief_view(state), fixed.fixed_view(brief, retrieval, cat), opts,
                             assemble.component_inputs([c for ids in opts.values() for c in ids]), limits)
    try:
        out, usage = _call(state, p, "planning", SiteDesign, prompts.site_system(cat, limits), user)
    except InvalidOutputError as error:
        return {"planning": _fail(p, "design_site", str(error))}
    p.site_design = assemble.tidy(out).model_dump(mode="json")
    return {"planning": p, "usage": usage}


def design_data(state: GraphState) -> dict:
    """Call 2, skipped when the site sends and shows no stored data."""
    p = _p(state)
    draft = assemble.build_plan(state["brief"], state["retrieval"], _site(p), None, load_catalogue())
    sections = assemble.data_sections(draft)
    if not assemble.needs_data(draft):
        p.data_design = None
        return {"planning": p}
    feature_ids = {s["feature_id"] for s in sections}
    starters = {k: v for k, v in prompts.DATA_STARTERS.items() if k in feature_ids}
    try:
        out, usage = _call(state, p, "planning", DataDesign, prompts.data_system(state["run_config"].limits),
                           prompts.data_user(_brief_view(state), sections, starters))
    except InvalidOutputError as error:
        return {"planning": _fail(p, "design_data", str(error))}
    p.data_design = out.model_dump(mode="json")
    return {"planning": p, "usage": usage}


def assemble_plan(state: GraphState) -> dict:
    return {"plan": _build(state, state["planning"])}


# ---------------------------------------------------------------- step 6
def check_plan(state: GraphState) -> dict:
    p, plan, limits = _p(state), state["plan"], state["run_config"].limits
    p.issues = checks.run_checks(plan, state["brief"], state["retrieval"], load_catalogue(), limits)
    update: dict = {"planning": p}
    if p.before_fix:
        before, p.before_fix = p.before_fix, None
        if not fix_helped(before["issues"], p.issues):   # worse or a swap (seen live): keep the earlier design
            p.site_design, p.data_design, p.issues = before["site_design"], before["data_design"], before["issues"]
            plan = update["plan"] = BuildPlan.model_validate(before["plan"])
    if not p.issues:
        p.status = "writing_text"
        return update
    if p.status == "changing" and p.before_change:        # the user's change broke the plan: undo it
        before = p.before_change
        p.site_design, p.data_design = before["site_design"], before["data_design"]
        p.before_change, p.status = None, "awaiting_approval"
        p.notice = "That change could not be made without breaking the plan, so the plan is unchanged."
        return {"planning": p, "plan": BuildPlan.model_validate(before["plan"])}
    if p.fix_rounds_used >= limits.max_plan_fix_rounds:
        update["planning"] = _fail(p, "check_plan", "; ".join(p.issues))
        return update
    p.status = "checking"
    return update


def fix_helped(before: list[str], after: list[str]) -> bool:
    """A fix is kept only when it leaves fewer problems and no check fails that passed before (D-214)."""
    failing = lambda issues: {i.split(":", 1)[0] for i in issues}     # check numbers, e.g. "8"
    return len(after) < len(before) and failing(after) <= failing(before)


def fix_plan(state: GraphState) -> dict:
    p = _p(state)
    p.fix_rounds_used += 1
    p.before_fix = {"site_design": p.site_design, "data_design": p.data_design, "issues": p.issues,
                    "plan": state["plan"].model_dump(mode="json")}
    return _redesign(state, p, "fix_plan", prompts.fix_user(_design(p), p.issues))


def _design(p: PlanningState) -> dict:
    return {"site": p.site_design, "data": p.data_design or {}}


def _redesign(state: GraphState, p: PlanningState, node: str, user: str) -> dict:
    try:
        out, usage = _call(state, p, "planning_fix", PlanFix, prompts.FIX_SYSTEM, user)
    except InvalidOutputError as error:
        return {"planning": _fail(p, node, str(error))}
    p.site_design = assemble.tidy(out.site).model_dump(mode="json")
    p.data_design = out.data.model_dump(mode="json") if (out.data.entities or out.data.routes) else None
    return {"planning": p, "usage": usage}


# ---------------------------------------------------------------- step 7
def _text_context(state: GraphState) -> dict:
    brief = state["brief"]
    return {"business_type": brief.business_type, "goal": brief.goal, "audience": brief.audience,
            "theme": (brief.theme or {}).get("params", {}),
            "features": [f.name for f in brief.features if f.tier != "unsupported"]}


def _slot_view(plan: BuildPlan, only: set[str] | None = None) -> list[dict]:
    pages = {pg.page_id: pg.title for pg in plan.pages}
    sections = {c.section_id: c for c in plan.components}
    required = texts.required_slots(plan)
    return [{"slot_id": t.slot_id, "page": pages.get(sections[t.section_id].page, "every page"),
             "feature": sections[t.section_id].feature_id, "input": t.prop, "max_length": t.max_length,
             "required": t.slot_id in required, "button": texts.is_button(t)}
            for t in plan.texts if only is None or t.slot_id in only]


def _apply_texts(plan: BuildPlan, out: SiteTexts, rules: texts.TextRules) -> None:
    written = {t.slot_id: t.text.strip() for t in out.texts}
    for t in plan.texts:
        if t.slot_id in written:
            t.text = written[t.slot_id]
    hero = next((t for t in plan.texts if t.slot_id == assemble.HERO_HEADLINE), None)
    if hero and out.hero_headlines:
        sub = next((t.text for t in plan.texts if t.slot_id == "home.hero.subheadline"), "")
        hero.text, hero.alternatives = texts.pick_hero(out.hero_headlines, hero, sub, rules)


def write_texts(state: GraphState) -> dict:
    p, plan = _p(state), state["plan"].model_copy(deep=True)
    rules = texts.rules_for(state["brief"], plan)
    try:
        out, usage = _call(state, p, "planning", SiteTexts, prompts.TEXT_SYSTEM,
                           prompts.text_user(_text_context(state), _slot_view(plan), sorted(rules.placeholders)))
    except InvalidOutputError as error:
        return {"planning": _fail(p, "write_texts", str(error))}
    _apply_texts(plan, out, rules)
    p.issues = [f"{k}: {'; '.join(v)}" for k, v in texts.text_problems(plan, rules).items()]
    return {"planning": p, "plan": plan, "usage": usage}


def rewrite_texts(state: GraphState) -> dict:
    """One rewrite round for the texts that broke the pitch rules (plan v2 §6)."""
    p, plan = _p(state), state["plan"].model_copy(deep=True)
    rules = texts.rules_for(state["brief"], plan)
    problems = texts.text_problems(plan, rules)
    p.text_rewrites_used += 1
    try:
        out, usage = _call(state, p, "planning_fix", SiteTexts, prompts.REWRITE_SYSTEM,
                           prompts.rewrite_user(_text_context(state), _slot_view(plan, set(problems)),
                                                sorted(rules.placeholders), problems))
    except InvalidOutputError as error:
        return {"planning": _fail(p, "rewrite_texts", str(error))}
    if assemble.HERO_HEADLINE not in problems:
        out.hero_headlines = []                    # keep the chosen hero
    _apply_texts(plan, out, rules)
    return {"planning": p, "plan": plan, "usage": usage}


def finish_texts(state: GraphState) -> dict:
    """Optional texts that still break a rule are left out; then the whole plan is checked once more."""
    p, plan = _p(state), state["plan"].model_copy(deep=True)
    rules = texts.rules_for(state["brief"], plan)
    required = texts.required_slots(plan)
    for sid in texts.check_all(plan.texts, rules):
        if sid not in required:
            next(t for t in plan.texts if t.slot_id == sid).text = ""
    p.issues = checks.run_checks(plan, state["brief"], state["retrieval"], load_catalogue(),
                                 state["run_config"].limits, with_texts=True)
    if p.issues:
        return {"planning": _fail(p, "finish_texts", "; ".join(p.issues)), "plan": plan}
    p.status, p.before_change = "awaiting_approval", None
    return {"planning": p, "plan": plan}


# ---------------------------------------------------------------- step 8
def await_plan_approval(state: GraphState) -> dict:
    """Interrupt only. The decision is stored; apply_decision acts on it."""
    raw = interrupt(plan_view(state["plan"], state["planning"], state["run_config"].limits),
                    response_schema=PlanDecision)
    decision = PlanDecision.model_validate(raw if isinstance(raw, dict) else raw.model_dump())
    p = _p(state)
    p.notice = None
    if decision.decision == "approve":
        p.status = "done"
    elif decision.decision == "cancel":
        p.status = "cancelled"
    else:
        p.status = "changing"
        p.pending_change = sanitise(decision.change_text or "", MAX_CHANGE_CHARS)[0]
    return {"planning": p}


def apply_change(state: GraphState) -> dict:
    p = _p(state)
    limits = state["run_config"].limits
    if not p.pending_change or p.edits_used >= limits.max_plan_edits:
        p.status, p.pending_change = "awaiting_approval", None
        p.notice = ("Please describe the change you want." if p.edits_used < limits.max_plan_edits
                    else "No more changes can be made to this plan. Approve it, or start over.")
        return {"planning": p}
    p.edits_used += 1
    p.before_change = {"site_design": p.site_design, "data_design": p.data_design,
                       "plan": state["plan"].model_dump(mode="json")}
    change, p.pending_change = p.pending_change, None
    return _redesign(state, p, "apply_change", prompts.fix_user(_design(p), [], change))


# ---------------------------------------------------------------- step 10
def freeze(state: GraphState) -> dict:
    plan = state["plan"].model_copy(deep=True)
    plan.status, plan.approved_at = "approved", datetime.now(timezone.utc)
    p = _p(state)
    p.status = "done"
    return {"planning": p, "plan": plan}
