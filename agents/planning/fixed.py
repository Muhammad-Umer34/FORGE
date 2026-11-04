# D:\FYP\FORGE-1\agents\planning\fixed.py
"""
Planning steps 1 and 2 (plan v2 §5), code only: check the input, then the parts every site has and the
choices the catalogue already answers. The model designs only what is left.
"""
from agents.catalogue import Catalogue
from agents.state import BriefFeature, ClarifiedBrief, RetrievalResult

# Placed by code on every site, never chosen by the model: (section id, component, feature).
LAYOUT = (("all.navbar", "navbar", "navigation"), ("all.footer", "footer", "footer"))
HERO = ("home.hero", "hero-banner", "hero-header")
PAGE_HEADER = ("page-header", "page-header")                  # (component, feature) on every inner page
CODE_FEATURES = {"navigation", "footer", "hero-header", "page-header"}
SITE_WIDE_ROLES = ("global", "overlay")
# Features built from several components used together: (main component, extra page component, route).
TOGETHER = {"blog": ("blog-list", "blog-post", "/blog/[slug]")}


def planned_features(brief: ClarifiedBrief) -> list[BriefFeature]:
    return [f for f in brief.features if f.tier != "unsupported"]


def check_input(brief: ClarifiedBrief | None, retrieval: RetrievalResult | None, cat: Catalogue) -> list[str]:
    """Step 1. Any problem here means something went wrong earlier, so the run stops."""
    if brief is None or brief.status != "ready" or brief.frozen_at is None:
        return ["the brief is not confirmed"]
    if retrieval is None:
        return ["components were not searched"]
    found = {c.feature_id for c in retrieval.candidates}
    problems = [f"no component found for '{f.id}'" for f in planned_features(brief)
                if f.tier == "catalogued" and f.id not in CODE_FEATURES and f.id not in found]
    problems += [f"unknown feature '{f.id}'" for f in planned_features(brief)
                 if f.tier == "catalogued" and f.id not in cat.features]
    if not brief.pages:
        problems.append("the brief has no pages")
    return problems


def site_wide(brief: ClarifiedBrief, cat: Catalogue) -> list[tuple[str, str, str]]:
    """Header, footer and the brief's site-wide parts (WhatsApp button, cookie notice...), placed once."""
    out = list(LAYOUT)
    for f in planned_features(brief):
        feature = cat.features.get(f.id)
        if feature and f.id not in CODE_FEATURES and feature.site_role in SITE_WIDE_ROLES:
            out.append((f"all.{f.id}", feature.component_ids[0], f.id))
    return out


def options(brief: ClarifiedBrief, retrieval: RetrievalResult, cat: Catalogue) -> dict[str, list[str]]:
    """Components the model may choose from, per feature that needs a section. Site-wide parts are not here."""
    wide = {fid for _, _, fid in site_wide(brief, cat)}
    out: dict[str, list[str]] = {}
    for f in planned_features(brief):
        if f.id in CODE_FEATURES or f.id in wide:
            continue
        found = [c.component_id for c in retrieval.candidates if c.feature_id == f.id]
        if f.id in TOGETHER:
            found = [TOGETHER[f.id][0]]
        out[f.id] = found
    return out


def fixed_view(brief: ClarifiedBrief, retrieval: RetrievalResult, cat: Catalogue) -> dict:
    """What the model is told code already placed or decided."""
    opts = options(brief, retrieval, cat)
    return {
        "site_wide": [sid for sid, _, _ in site_wide(brief, cat)],
        "home": "the hero banner is the first section of Home",
        "inner_pages": "every other page starts with a page header",
        "decided": {fid: ids[0] for fid, ids in opts.items() if len(ids) == 1 and fid in cat.features},
        "together": {fid: f"{extra} is placed by code on {route}" for fid, (_, extra, route) in TOGETHER.items()
                     if fid in opts},
    }
