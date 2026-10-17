# D:\FYP\FORGE-1\agents\clarification\grounding.py
"""
Grounding (code, no model): ties every requested item to the catalogue, the unsupported list or a
custom item, picks the site baseline, works out the pages, and proposes extras.
The model only suggests ids; this module checks every id exists before using it (D-113).
"""
import re

from agents.catalogue import Catalogue
from agents.clarification.schemas import IntakeItem
from agents.state import ClarificationState, FeatureMatch, Limits, ProposedExtra, RequestedItem

_WORD = re.compile(r"[\w']+", re.UNICODE)


def _words(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if len(w) > 2]


def evidence_found(evidence: str, source_text: str) -> bool:
    """True when the evidence words really appear in the user's text (guards against invented items)."""
    if not evidence.strip():
        return False
    if evidence.lower().strip() in source_text.lower():
        return True
    words = _words(evidence)
    source_words = set(_words(source_text))
    return bool(words) and all(w in source_words for w in words)


def items_from_model(c: ClarificationState, raw: list[IntakeItem], source_text: str) -> list[str]:
    """Append model-extracted items whose evidence is in the user's text. Returns flags for dropped items."""
    flags = []
    for it in raw:
        if not evidence_found(it.evidence, source_text):
            flags.append(f"dropped_unverified_item:{it.text[:40]}")
            continue
        c.requested_items.append(RequestedItem(
            item_id=f"i{len(c.requested_items) + 1}",
            text=it.text.strip(),
            kind=it.kind,
            evidence=it.evidence.strip(),
            candidate_feature_id=it.candidate_feature_id,
            alternative_feature_id=it.alternative_feature_id,
            candidate_capability_id=it.candidate_capability_id,
            is_core=it.is_core,
            retracted=it.retracted,
        ))
    return flags


_SITE_WORDS = {"website", "site", "web", "page", "pages", "webpage", "online", "presence", "for", "my", "our", "the"}


def _restates_purpose(item: RequestedItem, c: ClarificationState) -> bool:
    """'a website for my shop' describes the site, not a feature: it must never become a custom item."""
    words = set(_words(item.text))
    business = set(_words(c.business_type or ""))
    return bool(words) and words <= (_SITE_WORDS | business) and bool(words & {"website", "site", "web", "webpage"})


def _phrase_capability(text: str, cat: Catalogue) -> str | None:
    """Safety net only, used when the model found no catalogue feature (D-113)."""
    lowered = text.lower()
    for cap in cat.capabilities.values():
        if any(p.lower() in lowered for p in cap.phrases):
            return cap.capability_id
    return None


def add_match(c: ClarificationState, cat: Catalogue, feature_id: str, source: str,
              item: RequestedItem | None = None) -> None:
    if any(m.feature_id == feature_id for m in c.matches):
        return
    feature = cat.features[feature_id]
    c.matches.append(FeatureMatch(
        feature_id=feature_id,
        name=feature.name,
        tier="catalogued",
        priority="must",
        source=source,
        requested_item_id=item.item_id if item else None,
        evidence=item.evidence if item else None,
    ))
    if feature_id in c.removed_feature_ids:
        c.removed_feature_ids.remove(feature_id)


def remove_item_matches(c: ClarificationState, item_id: str) -> None:
    c.matches = [m for m in c.matches if m.requested_item_id != item_id]


def ground_items(c: ClarificationState, cat: Catalogue) -> None:
    """Resolve every 'unresolved' item. Already resolved or answered items are left alone."""
    for item in c.requested_items:
        if item.resolution != "unresolved":
            continue
        feature_id = item.candidate_feature_id if item.candidate_feature_id in cat.features else None
        alternative = item.alternative_feature_id if item.alternative_feature_id in cat.features else None
        capability = item.candidate_capability_id if item.candidate_capability_id in cat.capabilities else None

        if item.retracted:
            item.resolution = "dropped_by_user"
        elif capability:
            item.resolution, item.resolved_to = "unsupported", capability
        elif feature_id and alternative and alternative != feature_id:
            item.resolution = "ambiguous"            # becomes a question of kind C
        elif feature_id:
            item.resolution, item.resolved_to = "feature", feature_id
            add_match(c, cat, feature_id, "user_stated", item)
        elif item.kind in ("style", "content"):
            item.resolution, item.resolved_to = "noted", item.kind
            if item.kind == "style" and not c.style_hint:
                c.style_hint = item.text
        elif _restates_purpose(item, c):
            item.resolution, item.resolved_to = "noted", "purpose"
        elif (cap := _phrase_capability(item.text, cat)) is not None:
            item.resolution, item.resolved_to = "unsupported", cap
        elif item.kind == "integration":
            item.resolution, item.resolved_to = "unsupported", None   # an outside service not on the list
        else:
            item.resolution = "custom"                # needs generated code (tier 2)
            if "custom_item" not in c.risk_flags:
                c.risk_flags.append("custom_item")


def custom_items(c: ClarificationState) -> list[RequestedItem]:
    return [i for i in c.requested_items if i.resolution == "custom"]


def core_unsupported_items(c: ClarificationState) -> list[RequestedItem]:
    return [i for i in c.requested_items
            if i.resolution == "unsupported" and i.is_core and not i.alternative_accepted and i.resolved_to != "limit"]


def choose_baseline(c: ClarificationState, cat: Catalogue) -> str | None:
    """Starting template only, never a scope limit (D-134)."""
    if c.baseline_hint:
        return c.baseline_hint
    matched = {m.feature_id for m in c.matches}
    for baseline in cat.baselines:                    # sorted by priority
        if matched.intersection(baseline.signal_features):
            return baseline.baseline_id
    return "brochure" if c.is_business else None


def _baseline(cat: Catalogue, baseline_id: str | None):
    return next((b for b in cat.baselines if b.baseline_id == baseline_id), None)


def site_feature_ids(c: ClarificationState, cat: Catalogue) -> list[tuple[str, str]]:
    """(feature_id, source) of catalogue features on the site, before custom items. Layout parts excluded."""
    result: dict[str, str] = {}
    for m in c.matches:
        if m.tier == "catalogued" and cat.features[m.feature_id].inclusion != "always":
            result.setdefault(m.feature_id, m.source)
    for e in c.proposed_extras:
        if e.status == "accepted":
            result.setdefault(e.feature_id, "proposed_accepted")
    baseline = _baseline(cat, choose_baseline(c, cat))
    if baseline:
        for fid in baseline.default_features:
            result.setdefault(fid, "baseline_default")
    return [(fid, src) for fid, src in result.items() if fid not in c.removed_feature_ids]


def site_pages(c: ClarificationState, cat: Catalogue) -> list[str]:
    """Home first, then the baseline's pages, then each feature's main page, in catalogue page order."""
    pages = {"home"}
    baseline = _baseline(cat, choose_baseline(c, cat))
    if baseline:
        pages.update(baseline.default_pages)
    for fid, _ in site_feature_ids(c, cat):
        main = cat.features[fid].main_page
        if main:
            pages.add(main)
    order = ["home"] + [p for p in cat.page_kinds if p != "home"]
    return [p for p in order if p in pages]


def page_adding_features(c: ClarificationState, cat: Catalogue) -> list[str]:
    """Features that add a page of their own (candidates to drop when the site is too big)."""
    baseline = _baseline(cat, choose_baseline(c, cat))
    fixed = {"home"} | set(baseline.default_pages if baseline else ())
    return [fid for fid, _ in site_feature_ids(c, cat)
            if (cat.features[fid].main_page or "home") not in fixed]


def propose_extras(c: ClarificationState, cat: Catalogue, limits: Limits) -> None:
    """Up to max_extras_shown 'suggest' features that fit the business. Never added silently (D-131)."""
    if c.proposed_extras:
        return  # proposed once per run
    on_site = {fid for fid, _ in site_feature_ids(c, cat)}
    business = (c.business_type or "").lower()

    def fits(types: tuple[str, ...]) -> int:
        if business and any(business in t or t in business for t in types):
            return 2
        return 1 if "any small business" in types else 0

    candidates = sorted(
        (f for f in cat.features.values()
         if f.inclusion == "suggest" and f.feature_id not in on_site and f.site_role != "global"
         and fits(f.business_types)),
        key=lambda f: -fits(f.business_types),
    )
    for f in candidates[:limits.max_extras_shown]:
        reason = f"Often useful for a {c.business_type}" if fits(f.business_types) == 2 else "Useful for most small businesses"
        c.proposed_extras.append(ProposedExtra(feature_id=f.feature_id, name=f.name, reason=reason))
