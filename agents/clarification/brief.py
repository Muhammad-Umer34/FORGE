# D:\FYP\FORGE-1\agents\clarification\brief.py
"""
Brief assembly (code only), the clarified_text template (D-117), the code checks and the
mechanical repair, and the confirmation screen payload (D-106, D-118).
The brief carries feature ids only; Context Retrieval chooses components (D-116).
"""
import re

from agents.catalogue import Catalogue
from agents.clarification import grounding
from agents.clarification.schemas import NO_VISITOR_ACTION, VISITOR_ACTION_FEATURES
from agents import theming
from agents.clarification.slots import get_slot
from agents.state import (
    BriefFeature, ClarificationState, ClarifiedBrief, Limits, UnsupportedItem,
)

_MUST_SOURCES = {"user_stated", "user_confirmed", "user_delegated"}
_EMBED_FEATURES = {"location-map": "map", "video": "video", "whatsapp-chat": "whatsapp"}
_ACTION_PHRASES = {
    "contact-form": "send you a message",
    "order-request": "send an order request",
    "booking": "book a time",
    "whatsapp-chat": "message you on WhatsApp",
}
_LIMIT_REASON = "More than one website of this size can include."


def _slug(text: str) -> str:
    return "custom-" + (re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "item")


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def draft_brief(c: ClarificationState, cat: Catalogue, version: int = 1) -> ClarifiedBrief:
    features: list[BriefFeature] = []
    for fid, source in grounding.site_feature_ids(c, cat):
        match = next((m for m in c.matches if m.feature_id == fid), None)
        features.append(BriefFeature(
            id=fid,
            name=cat.features[fid].name,
            priority="must" if source in _MUST_SOURCES else "should",
            source=source,
            requested_item_id=match.requested_item_id if match else None,
        ))
    for item in grounding.custom_items(c):
        features.append(BriefFeature(
            id=_slug(item.text), name=item.text, description="Custom feature: needs generated code",
            priority="must", source="user_stated", tier="custom", requested_item_id=item.item_id,
        ))

    feature_ids = [f.id for f in features if f.tier == "catalogued"]
    pages = [
        {"name": page, "sections": [fid for fid in feature_ids if (cat.features[fid].main_page or "home") == page]}
        for page in grounding.site_pages(c, cat)
    ]

    unsupported = []
    for item in c.requested_items:
        if item.resolution != "unsupported":
            continue
        if item.resolved_to == "limit":
            unsupported.append(UnsupportedItem(asked=item.text, group="limit", reason=_LIMIT_REASON,
                                               acknowledged_by_user=True))
            continue
        cap = cat.capabilities.get(item.resolved_to or "")
        unsupported.append(UnsupportedItem(
            asked=item.text,
            capability_id=cap.capability_id if cap else None,
            group=cap.group if cap else "unknown",
            reason=cap.reason if cap else "This outside service is not something FORGE can connect to.",
            alternative_text=cap.alternative_text if cap else "",
            alternative_feature_ids=list(cap.alternative_feature_ids) if cap else [],
            acknowledged_by_user=item.alternative_accepted,
        ))

    brief = ClarifiedBrief(
        version=version,
        baseline=grounding.choose_baseline(c, cat),
        business_type=c.business_type,
        goal=c.goal or "",
        features=features,
        pages=pages,
        content_needs=sorted({k for fid in feature_ids for k in cat.features[fid].content_needs}),
        theme=chosen_theme(c),
        integrations=[{"kind": _EMBED_FEATURES[fid], "feature_id": fid} for fid in feature_ids if fid in _EMBED_FEATURES],
        unsupported=unsupported,
        assumptions=list(c.assumptions),
    )
    brief.clarified_text = clarified_text(brief, c)
    return brief


def theme_candidates(c: ClarificationState) -> list[dict]:
    """Three generated themes for this request (D-157). Deterministic: same request, same themes."""
    return theming.candidates(c.business_type, c.personality, c.hue_family, c.brand_colour, c.prefers_dark)


def chosen_theme(c: ClarificationState) -> dict:
    """The theme the user picked on the confirmation screen, else the pre-selected candidate."""
    themes = theme_candidates(c)
    picked = get_slot(c, "style").values
    return next((t for t in themes if picked and t["theme_id"] == picked[0]), None) or next(t for t in themes if t["selected"])


def clarified_text(brief: ClarifiedBrief, c: ClarificationState) -> str:
    """Plain-language summary built only from the brief, so it cannot invent anything (D-117)."""
    parts = []
    n = len(brief.pages)
    if brief.business_type:
        parts.append(f"A {n}-page website for {_article(brief.business_type)} {brief.business_type}.")
    else:
        parts.append(f"A {n}-page website.")
    if brief.goal:
        parts.append(f"Goal: {brief.goal.rstrip('.')}.")
    actions = [f.id for f in brief.features if f.id in VISITOR_ACTION_FEATURES]
    if actions:
        phrases = [_ACTION_PHRASES[a] for a in actions]
        joined = phrases[0] if len(phrases) == 1 else ", ".join(phrases[:-1]) + " or " + phrases[-1]
        parts.append(f"Visitors can {joined}.")
    elif NO_VISITOR_ACTION in get_slot(c, "visitor_actions").values:
        parts.append("The site shows information only; visitors do not send anything through it.")
    names = [f.name for f in brief.features if f.id not in VISITOR_ACTION_FEATURES]
    if names:
        parts.append("It includes: " + ", ".join(names) + ".")
    if brief.theme:
        parts.append(f"Look: {brief.theme['label']}, with {brief.theme['fonts']['heading']} headings.")
    for u in brief.unsupported:
        note = u.alternative_text or u.reason
        parts.append(f'Not included: "{u.asked}" ({note.rstrip(".")}).')
    return " ".join(parts)


def code_checks(brief: ClarifiedBrief, c: ClarificationState, cat: Catalogue, limits: Limits) -> list[str]:
    """The checks from v6 Section 11. An empty list means the brief passed."""
    issues = []
    try:
        ClarifiedBrief.model_validate(brief.model_dump())
    except Exception as error:  # pydantic ValidationError
        issues.append(f"schema: {error}")
    open_items = [i.text for i in c.requested_items if i.resolution in ("unresolved", "ambiguous")]
    if open_items:
        issues.append("unresolved requested items: " + ", ".join(open_items))
    for f in brief.features:
        if f.tier == "catalogued" and f.id not in cat.features:
            issues.append(f"unknown feature id: {f.id}")
    unsupported_ids = {i.item_id for i in c.requested_items if i.resolution == "unsupported"}
    for f in brief.features:
        if f.requested_item_id in unsupported_ids and f.source == "user_stated":
            issues.append(f"unsupported item inside features: {f.id}")
    ids = [f.id for f in brief.features]
    if len(ids) != len(set(ids)):
        issues.append("duplicate features")
    pending = {e.feature_id for e in c.proposed_extras if e.status == "pending"}
    if pending.intersection(ids):
        issues.append("pending extra inside features")
    unknown_keys = set(brief.content_needs) - set(cat.content_keys)
    if unknown_keys:
        issues.append(f"unknown content keys: {sorted(unknown_keys)}")
    if sum(1 for f in brief.features if f.tier == "custom") > limits.max_custom_features:
        issues.append("too many custom features")
    if len(brief.pages) > limits.max_pages:
        issues.append("too many pages")
    for u in brief.unsupported:
        if not (u.alternative_text or u.reason):
            issues.append(f"unsupported item without a note: {u.asked}")
    for name in ("purpose", "visitor_actions"):
        if get_slot(c, name).status != "answered":
            issues.append(f"blocking slot not answered: {name}")
    return issues


def repair(brief: ClarifiedBrief, c: ClarificationState) -> ClarifiedBrief:
    """Mechanical fixes only (v5 rules): drop duplicates, move pending extras back out of features."""
    pending = {e.feature_id for e in c.proposed_extras if e.status == "pending"}
    seen: set[str] = set()
    kept = []
    for f in brief.features:
        if f.id in seen or f.id in pending:
            continue
        seen.add(f.id)
        kept.append(f)
    brief.features = kept
    brief.clarified_text = clarified_text(brief, c)
    return brief


_SWATCH_TOKENS = ("background", "card", "foreground", "muted", "primary", "primary-foreground", "accent")


def _theme_card(theme: dict) -> dict:
    """What the confirmation screen needs to preview a theme: real computed colours, fonts and radius."""
    return {
        "id": theme["theme_id"], "kind": theme["kind"], "label": theme["label"], "reason": theme["reason"],
        "fonts": theme["fonts"], "radius": theme["radius"], "default_mode": theme["default_mode"],
        "swatch": {mode: {k: theme["tokens"][mode][k] for k in _SWATCH_TOKENS} for mode in ("light", "dark")},
    }


def brief_view_for_model(brief: ClarifiedBrief) -> dict:
    """What the review and test-generation calls see: no business detail values, no raw prompt."""
    return {
        "business_type": brief.business_type,
        "goal": brief.goal,
        "pages": brief.pages,
        "features": [{"id": f.id, "name": f.name, "priority": f.priority, "source": f.source, "tier": f.tier}
                     for f in brief.features],
        "NOT INCLUDED": [u.asked for u in brief.unsupported],
    }


def confirmation_payload(brief: ClarifiedBrief, c: ClarificationState, limits: Limits, edit_allowed: bool) -> dict:
    """The confirmation screen (v6 Section 12). Built by code; shown at the second interrupt."""
    selected = chosen_theme(c)["theme_id"]
    return {
        "type": "confirmation",
        "summary": brief.clarified_text,
        "pages": [p["name"] for p in brief.pages],
        "features": [{"id": f.id, "name": f.name, "source": f.source,
                      "can_untick": f.source == "baseline_default"} for f in brief.features],
        "extras": [{"id": e.feature_id, "name": e.name, "reason": e.reason}
                   for e in c.proposed_extras if e.status == "pending"],
        "themes": [_theme_card(t) for t in theme_candidates(c)],
        "theme_selected": selected,
        "limits_notice": [{"asked": u.asked, "reason": u.reason, "alternative": u.alternative_text}
                          for u in brief.unsupported],
        "assumptions": [a.text for a in brief.assumptions],
        "please_check": c.check.issues if c.check and c.check.reviewed_by_model else [],
        "business_details_note": "Your business details (name, phone, photos) are collected in the next step.",
        "edits_left": max(0, limits.max_confirmation_edits - c.confirmation.edits_used) if edit_allowed else 0,
        "actions": ["confirm", "edit", "cancel"] if edit_allowed and c.confirmation.edits_used < limits.max_confirmation_edits
                   else ["confirm", "cancel"],
    }
