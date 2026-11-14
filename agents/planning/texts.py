# D:\FYP\FORGE-1\agents\planning\texts.py
"""
Pitch rules for website text (plan v2 §6, D-205), checked by code. Text must sell this business: tied to its
type and goal, never generic, never an invented fact, within length, buttons start with a verb, no two
sections share a title, and real facts only as allowed placeholders such as {business_name}.
"""
import re
from dataclasses import dataclass

from agents.planning.content_schema import needs_of
from agents.planning.fixed import SEO, SEO_TEXT
from agents.retrieval.ranker import words
from agents.state import BuildPlan, ClarifiedBrief, TextSlot

HERO = "home.hero."
MAX_HEADLINE_WORDS = 8
MAX_SUBHEADLINE_WORDS = 25
GENERIC = ("welcome to", "one-stop", "one stop", "quality service", "look no further", "we are the best",
           "your trusted partner", "second to none", "world-class", "world class", "state-of-the-art",
           "unparalleled", "lorem", "click here", "best in town", "your website", "our website")
CLAIMS = ("award", "certified", "number one", "no. 1", "#1", "the best", "best-rated", "top-rated", "top rated",
          "leading", "years of experience", "since 19", "since 20", "rated", "stars", "guarantee", "cheapest",
          "lowest price", "trusted by", "satisfied clients", "happy customers")
FACT_PATTERN = re.compile(r"\d|[$€£₨%]|\brs\.?\s|\bpkr\b", re.IGNORECASE)
PLACEHOLDER = re.compile(r"\{(\w+)\}")
VERBS = {"book", "call", "see", "view", "get", "start", "explore", "browse", "contact", "order", "send", "discover",
         "join", "subscribe", "shop", "visit", "try", "request", "learn", "reserve", "message", "chat", "read",
         "meet", "check", "find", "plan", "schedule", "sign", "claim", "ask", "email", "choose", "submit",
         "confirm", "apply", "enquire", "inquire", "watch", "follow", "talk", "write", "show", "make", "tell",
         "pick", "grab", "taste", "come", "drop", "let", "share", "download", "go", "hire", "secure", "save",
         "accept", "decline", "reject", "allow", "donate", "give", "support", "enroll", "enrol", "register",
         "buy", "add", "open", "reply", "connect"}


# Feature names that say nothing about the business ("About us", "Contact form"): not counted as business words.
_GENERIC_FEATURE_WORDS = words("about story contact form info information detail call action navigation footer "
                               "header hero social link back top cookie notice legal faq announcement key stat "
                               "content row page header search filter video")


@dataclass
class TextRules:
    relevance: set[str]                 # words of this business; the hero must use at least one
    placeholders: set[str]              # content keys allowed as {key}


def rules_for(brief: ClarifiedBrief, plan: BuildPlan) -> TextRules:
    # Business type, goal, audience and the must features' names, without names that fit any site ("about",
    # "contact"), which would let any text pass (KI-20: vague briefs gave too few words).
    features = " ".join(f.name for f in brief.features if f.priority == "must" and f.tier != "unsupported")
    relevance = words(" ".join((brief.business_type or "", brief.goal, brief.audience)))
    relevance |= words(features) - _GENERIC_FEATURE_WORDS
    keys = {f.key for f in plan.content_schema if f.kind == "fact"} | {"business_name"}
    return TextRules(relevance=relevance, placeholders=keys)


def is_button(slot: TextSlot) -> bool:
    """ctaText, buttonLabel, submitButtonText... are buttons; cta_body or ctaTitle are not (KI-21)."""
    prop = re.sub(r"[^a-z]", "", slot.prop.lower())
    return ("cta" in prop or "button" in prop) and (prop.endswith(("text", "label")) or prop in ("cta", "button"))


def _plain(text: str) -> str:
    return PLACEHOLDER.sub("", text)


def check_text(slot: TextSlot, text: str, rules: TextRules) -> list[str]:
    """Problems with one text, in plain words the rewrite prompt can act on."""
    if not text.strip():
        return []
    problems, low = [], text.lower()
    if len(text) > slot.max_length:
        problems.append(f"longer than {slot.max_length} characters")
    n_words = len(text.split())
    if slot.prop == "headline" and n_words > MAX_HEADLINE_WORDS:
        problems.append(f"more than {MAX_HEADLINE_WORDS} words")
    if slot.prop in ("subheadline", "subtitle") and n_words > MAX_SUBHEADLINE_WORDS:
        problems.append(f"more than {MAX_SUBHEADLINE_WORDS} words")
    problems += [f"generic phrase '{g}'" for g in GENERIC if g in low]
    problems += [f"invented claim '{c}'" for c in CLAIMS if re.search(rf"(?<!\w){re.escape(c)}(?!\w)", low)]
    if FACT_PATTERN.search(_plain(text)):
        problems.append("a number or price: real facts only as placeholders")
    problems += [f"placeholder {{{p}}} is not allowed" for p in PLACEHOLDER.findall(text) if p not in rules.placeholders]
    if is_button(slot) and re.sub(r"[^a-z]", "", re.split(r"['’]", low.split()[0])[0]) not in VERBS:   # "Let's" -> let
        problems.append("a button must start with a verb")
    return problems


def check_all(texts: list[TextSlot], rules: TextRules, relevance: bool = True) -> dict[str, list[str]]:
    """Problems per slot id, including repeated titles and (unless `relevance` is off) a hero that is not about this
    business. The relevance rule asks for a rewrite but never ends planning: a headline the owner can change in one
    click is not worth a failed run (KI-20); the plan screen says so instead."""
    out: dict[str, list[str]] = {}
    for t in texts:
        if problems := check_text(t, t.text, rules):
            out[t.slot_id] = problems
    titles: dict[str, str] = {}
    for t in texts:
        if t.prop in ("title", "headline") and t.text.strip():
            key = t.text.strip().lower()
            if key in titles:
                out.setdefault(t.slot_id, []).append(f"same title as {titles[key]}")
            titles.setdefault(key, t.slot_id)
    hero = " ".join(t.text for t in texts if t.slot_id.startswith(HERO) and t.prop in ("headline", "subheadline"))
    if relevance and hero.strip() and not hero_is_relevant(texts, rules):
        out.setdefault(HERO + "headline", []).append(
            "the hero does not say what this business offers; use words such as " + ", ".join(sorted(rules.relevance)[:8]))
    return out


def text_problems(plan: BuildPlan, rules: TextRules) -> dict[str, list[str]]:
    """check_all plus required texts the model left empty, so they reach the rewrite round (KI-03)."""
    out = check_all(plan.texts, rules)
    for sid in sorted(required_slots(plan) - {t.slot_id for t in plan.texts if t.text.strip()}):
        out.setdefault(sid, []).append("required text is missing")
    return out


def hero_is_relevant(texts: list[TextSlot], rules: TextRules) -> bool:
    hero = " ".join(t.text for t in texts if t.slot_id.startswith(HERO) and t.prop in ("headline", "subheadline"))
    return not hero.strip() or not rules.relevance or bool(words(_plain(hero)) & rules.relevance)


def pick_hero(candidates: list[str], slot: TextSlot, subheadline: str, rules: TextRules) -> tuple[str, list[str]]:
    """The first candidate (the model's order) that passes every rule; the others are kept as alternatives."""
    clean = [c.strip() for c in candidates if c.strip()]
    for c in clean:
        if not check_text(slot, c, rules) and words(_plain(f"{c} {subheadline}")) & rules.relevance:
            return c, [x for x in clean if x != c]
    return (clean[0] if clean else ""), clean[1:]


def required_slots(plan: BuildPlan) -> set[str]:
    """Text slots whose component input is required, plus every page's search title and description: check 17 needs
    both, so a description that breaks a rule must be rewritten, not left out (found in the Group 2 evaluation)."""
    specs = {s.spec_id: s for s in plan.custom_specs}
    return {f"{c.section_id}.{n['name']}" for c in plan.components for n in needs_of(c, specs)
            if n["kind"] == "copy" and (n.get("required", True) or (c.component_id == SEO[1] and n["name"] in SEO_TEXT))}
