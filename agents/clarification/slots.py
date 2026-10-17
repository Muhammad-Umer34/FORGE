# D:\FYP\FORGE-1\agents\clarification\slots.py
"""
The fixed slot checklist, gap detection and question selection (code, no model) - decisions
D-101, D-102, D-104, D-105, D-112. The model only extracts values; this module decides what is
missing, what blocks the build, which question comes next, and applies option answers.
"""
from dataclasses import dataclass, field

from agents.catalogue import Catalogue
from agents.clarification import grounding
from agents.clarification.schemas import NO_VISITOR_ACTION, VISITOR_ACTION_FEATURES, UserAnswer
from agents.state import Assumption, ClarificationState, Limits, OutOfScopeInfo, Question, QuestionOption, Slot

STYLE_THEMES = ("warm", "clean", "bold")     # PLACEHOLDER: theme list is open question Q-04

# "You decide" for visitor actions picks the baseline's usual way of being contacted.
_DEFAULT_VISITOR_ACTION = {"booking": "booking", "catalog": "order-request"}
_VISITOR_ACTION_LABELS = {
    "contact-form": "A contact form",
    "order-request": "Send an order request",
    "booking": "Book a time",
    "whatsapp-chat": "Message on WhatsApp",
    NO_VISITOR_ACTION: "Just show information",
}


def init_slots() -> list[Slot]:
    return [
        Slot(name="purpose", importance="blocking"),
        Slot(name="visitor_actions", importance="blocking"),
        Slot(name="style", importance="optional"),
    ]


def get_slot(c: ClarificationState, name: str) -> Slot:
    return next(s for s in c.slots if s.name == name)


def fill_slots_from_items(c: ClarificationState) -> None:
    """Fill slots that the request itself already answers. Never overwrites an answered slot."""
    actions = get_slot(c, "visitor_actions")
    if actions.status != "answered":
        found = [m.feature_id for m in c.matches if m.feature_id in VISITOR_ACTION_FEATURES]
        if found:
            actions.status, actions.values, actions.source = "answered", found, "user_stated"


@dataclass
class Gap:
    kind: str            # question kind A-E
    key: str             # slot name, "item:<id>", "custom_limit" or "page_limit"
    missing: str         # plain words for a missing_info failure
    item_id: str | None = None
    extra: dict = field(default_factory=dict)


def open_gaps(c: ClarificationState, cat: Catalogue, limits: Limits) -> list[Gap]:
    """Blocking gaps in the order they are asked: purpose, core unsupported, visitor actions, ambiguity, size."""
    gaps: list[Gap] = []
    if get_slot(c, "purpose").status != "answered":
        gaps.append(Gap("A", "purpose", "what the website is for"))
    for item in grounding.core_unsupported_items(c):
        gaps.append(Gap("D", f"item:{item.item_id}", f"whether to continue without '{item.text}'", item.item_id))
    if get_slot(c, "visitor_actions").status != "answered":
        gaps.append(Gap("B", "visitor_actions", "how visitors should contact you or order"))
    for item in c.requested_items:
        if item.resolution == "ambiguous":
            gaps.append(Gap("C", f"item:{item.item_id}", f"what you meant by '{item.text}'", item.item_id))
    if len(grounding.custom_items(c)) > limits.max_custom_features:
        gaps.append(Gap("E", "custom_limit", "which special features to keep"))
    if len(grounding.site_pages(c, cat)) > limits.max_pages:
        gaps.append(Gap("E", "page_limit", "which pages to keep"))
    return gaps


def times_asked(c: ClarificationState, key: str) -> int:
    return sum(1 for q in c.questions if q.slot == key)


def free_text_allowed(c: ClarificationState, limits: Limits) -> bool:
    """Free text costs a model call; one call is always reserved for test generation."""
    return c.calls_used < limits.call_hard_cap - 1


def build_question(gap: Gap, c: ClarificationState, cat: Catalogue, limits: Limits) -> Question:
    """Template wording, options from the catalogue (D-105, D-125)."""
    number = len(c.questions) + 1
    other = free_text_allowed(c, limits)
    common = dict(question_id=f"q{number}", number=number, kind=gap.kind, slot=gap.key)

    if gap.kind == "A":
        return Question(**common, text="What is this website for?",
                        options=[QuestionOption(option_id=b.baseline_id, label=b.label) for b in cat.baselines],
                        allow_other_text=other)

    if gap.kind == "B":
        recommended = _DEFAULT_VISITOR_ACTION.get(grounding.choose_baseline(c, cat) or "", "contact-form")
        return Question(**common, text="How should visitors contact you or order?", multi_select=True,
                        options=[QuestionOption(option_id=o, label=_VISITOR_ACTION_LABELS[o], recommended=o == recommended)
                                 for o in (*VISITOR_ACTION_FEATURES, NO_VISITOR_ACTION)],
                        allow_you_decide=True, allow_other_text=other)

    item = next((i for i in c.requested_items if i.item_id == gap.item_id), None)
    if gap.kind == "C" and item:
        ids = [item.candidate_feature_id, item.alternative_feature_id]
        return Question(**common, text=f'Which of these did you mean by "{item.text}"?',
                        options=[QuestionOption(option_id=f, label=cat.features[f].name) for f in ids],
                        allow_you_decide=True, allow_other_text=other)

    if gap.kind == "D" and item:
        cap = cat.capabilities.get(item.resolved_to or "")
        alternative = cap.alternative_text if cap and cap.alternative_text else "We can build the rest of the site without it."
        return Question(**common, text=f'We can\'t build "{item.text}". {alternative} Continue with that?',
                        options=[QuestionOption(option_id="yes", label="Yes, use that", recommended=True),
                                 QuestionOption(option_id="no", label="No, stop")])

    if gap.key == "custom_limit":
        return Question(**common, multi_select=True, max_selections=limits.max_custom_features,
                        text=f"We can build up to {limits.max_custom_features} special features on one site. Which should we keep?",
                        options=[QuestionOption(option_id=i.item_id, label=i.text) for i in grounding.custom_items(c)])

    # page_limit
    candidates = grounding.page_adding_features(c, cat)
    keep = max(1, limits.max_pages - (len(grounding.site_pages(c, cat)) - len(candidates)))
    return Question(**common, multi_select=True, max_selections=keep,
                    text=f"That is more pages than we can build in one site. Which {keep} should we keep?",
                    options=[QuestionOption(option_id=f, label=cat.features[f].name) for f in candidates])


def select_next(c: ClarificationState, cat: Catalogue, limits: Limits) -> tuple[str, object]:
    """
    ("ask", Question) | ("draft", None) | ("fail", [missing...]).
    Blocking gaps are never filled with a default (D-112): when questions run out, the run fails
    and the missing information is listed.
    """
    gaps = open_gaps(c, cat, limits)
    if not gaps:
        return "draft", None
    gap = gaps[0]
    if c.questions_used >= limits.max_questions or times_asked(c, gap.key) > limits.max_reasks_per_slot:
        return "fail", [g.missing for g in gaps]
    if gap.key in ("purpose", "visitor_actions"):
        get_slot(c, gap.key).asks += 1
    return "ask", build_question(gap, c, cat, limits)


def validate_answer(q: Question, answer: UserAnswer) -> str | None:
    """Return an error message when the answer does not fit the question (the API turns it into HTTP 422)."""
    if answer.question_id != q.question_id:
        return f"answer is for {answer.question_id}, but the open question is {q.question_id}"
    allowed = {o.option_id for o in q.options}
    if answer.kind == "option":
        if not answer.option_ids or any(o not in allowed for o in answer.option_ids):
            return "option_ids must be chosen from the question's options"
        if not q.multi_select and len(answer.option_ids) != 1:
            return "this question takes exactly one option"
        if q.max_selections and len(answer.option_ids) > q.max_selections:
            return f"choose at most {q.max_selections} options"
    elif answer.kind == "you_decide" and not q.allow_you_decide:
        return "'You decide' is not allowed for this question"
    elif answer.kind == "other" and (not q.allow_other_text or not (answer.text or "").strip()):
        return "a typed answer is not allowed for this question, or the text is empty"
    return None


def apply_option_answer(c: ClarificationState, q: Question, option_ids: list[str], cat: Catalogue,
                        delegated: bool = False) -> None:
    """Apply chosen options by code (no model call). `delegated` marks a 'You decide' choice."""
    source = "user_delegated" if delegated else "user_confirmed"

    if q.kind == "A":
        baseline = next(b for b in cat.baselines if b.baseline_id == option_ids[0])
        c.baseline_hint = baseline.baseline_id
        c.goal = c.goal or baseline.label
        slot = get_slot(c, "purpose")
        slot.status, slot.values, slot.source = "answered", [baseline.baseline_id], source

    elif q.kind == "B":
        slot = get_slot(c, "visitor_actions")
        slot.status, slot.values, slot.source = "answered", option_ids, source
        for fid in option_ids:
            if fid != NO_VISITOR_ACTION:
                grounding.add_match(c, cat, fid, source)

    elif q.kind == "C":
        item = next(i for i in c.requested_items if f"item:{i.item_id}" == q.slot)
        item.resolution, item.resolved_to = "feature", option_ids[0]
        grounding.add_match(c, cat, option_ids[0], source, item)

    elif q.kind == "D":
        item = next(i for i in c.requested_items if f"item:{i.item_id}" == q.slot)
        cap = cat.capabilities.get(item.resolved_to or "")
        if option_ids[0] == "yes":
            item.alternative_accepted = True
            if cap and cap.alternative_feature_ids:
                grounding.add_match(c, cat, cap.alternative_feature_ids[0], "user_confirmed", item)
        else:
            reason = cap.reason if cap else "This is not something FORGE can build."
            c.out_of_scope = OutOfScopeInfo(
                reason=f'FORGE can\'t build "{item.text}". {reason}',
                alternatives=[cap.alternative_text] if cap and cap.alternative_text else [],
            )

    elif q.slot == "custom_limit":
        for item in grounding.custom_items(c):
            if item.item_id not in option_ids:
                item.resolution, item.resolved_to = "unsupported", "limit"

    elif q.slot == "page_limit":
        for fid in grounding.page_adding_features(c, cat):
            if fid not in option_ids:
                c.removed_feature_ids.append(fid)
                for item in c.requested_items:
                    if item.resolved_to == fid:
                        item.resolution, item.resolved_to = "unsupported", "limit"
                        grounding.remove_item_matches(c, item.item_id)


def apply_you_decide(c: ClarificationState, q: Question, cat: Catalogue) -> None:
    """'You decide': pick the default and log it as an Assumption the user will see (source user_delegated)."""
    if q.kind == "B":
        choice = _DEFAULT_VISITOR_ACTION.get(grounding.choose_baseline(c, cat) or "", "contact-form")
    else:  # C
        item = next(i for i in c.requested_items if f"item:{i.item_id}" == q.slot)
        choice = item.candidate_feature_id
    apply_option_answer(c, q, [choice], cat, delegated=True)
    c.assumptions.append(Assumption(
        text=f"{cat.features[choice].name} chosen for you",
        reason=f'You chose "You decide" for: {q.text}',
        default_applied=choice,
    ))
    if "you_decide_used" not in c.risk_flags:
        c.risk_flags.append("you_decide_used")
