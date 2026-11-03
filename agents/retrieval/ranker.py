# D:\FYP\FORGE-1\agents\retrieval\ranker.py
"""
Context Retrieval (plan v2, step 0): the catalogue components that can build each feature of the brief.
Code only, no model and no embeddings: with a few dozen components the catalogue already knows the answer.

- A catalogued feature gets every component of that feature (score 1.0). Booking and gallery have two to
  choose from; blog has two parts that are used together.
- A custom feature gets the components whose words match at least half of the feature's own words, best
  first, at most MAX_CUSTOM_MATCHES. A weak match returns nothing, so the part stays custom instead of being
  forced into a component that does not fit.
- Unsupported items and ids the catalogue does not know never get candidates.
"""
import re

from agents.catalogue import Catalogue, Component, load_catalogue
from agents.state import ClarifiedBrief, ComponentCandidate, RetrievalResult

MIN_MATCH = 0.5          # share of the custom feature's words that must appear in the component
MAX_CUSTOM_MATCHES = 3
_STOP = {"a", "an", "and", "the", "of", "for", "to", "with", "on", "in", "my", "our", "your", "their", "where",
         "can", "that", "this", "it", "is", "be", "show", "shows", "page", "section", "website", "site", "custom",
         "feature", "needs", "generated", "code", "want", "need", "like", "some", "add"}


def words(text: str) -> set[str]:
    """Lower-case content words, with a plural 's' removed so "stamps" matches "stamp"."""
    out = set()
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in _STOP or len(word) < 3:
            continue
        out.add(word[:-1] if word.endswith("s") and len(word) > 3 else word)
    return out


def _component_words(c: Component) -> set[str]:
    return words(" ".join((c.name, c.description, *c.keywords, *c.user_phrases)))


def keyword_matches(text: str, cat: Catalogue) -> list[tuple[str, float]]:
    """(component_id, score) for components matching at least MIN_MATCH of the text's words, best first."""
    wanted = words(text)
    if not wanted:
        return []
    scored = []
    for c in cat.components.values():
        if c.site_role == "global" and c.feature_id in ("navigation", "footer"):
            continue                                  # layout parts are placed by Planning, never matched
        share = len(wanted & _component_words(c)) / len(wanted)
        if share >= MIN_MATCH:   # words in the component's own name break ties ("price list" -> Services Price List)
            scored.append((c.component_id, round(share + 0.1 * len(wanted & words(c.name)) / len(wanted), 3)))
    scored.sort(key=lambda s: (-s[1], s[0]))
    return scored[:MAX_CUSTOM_MATCHES]


def rank_and_retrieve_components(brief: ClarifiedBrief) -> RetrievalResult:
    cat = load_catalogue()
    candidates: list[ComponentCandidate] = []
    for f in brief.features:
        if f.tier == "catalogued" and f.id in cat.features:
            candidates += [ComponentCandidate(component_id=cid, score=1.0, feature_id=f.id)
                           for cid in cat.features[f.id].component_ids]
        elif f.tier == "custom":
            # The custom feature's name is the user's own words; its description is a fixed label.
            candidates += [ComponentCandidate(component_id=cid, score=score, feature_id=f.id)
                           for cid, score in keyword_matches(f.name, cat)]
    return RetrievalResult(candidates=candidates)
