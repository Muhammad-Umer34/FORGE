# D:\FYP\FORGE-1\agents\catalogue.py
"""
Shared, read-only access to the component catalogue, the unsupported list and the
site baselines (decision D-129). Every agent reads catalogue data through this module
so there is one loader and one version hash.

A *feature* is a catalogue featureId. Several components can share one feature
(for example booking-form and appointment-slot-picker are both "booking").
"""
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

COMPONENTS_DIR = Path(__file__).resolve().parents[1] / "components"
CATALOG_FILE = COMPONENTS_DIR / "components_catalog.json"
UNSUPPORTED_FILE = COMPONENTS_DIR / "unsupported_capabilities.json"
BASELINES_FILE = COMPONENTS_DIR / "site_baselines.json"
EMBEDDINGS_FILE = COMPONENTS_DIR / "component_embeddings.json"

# Stronger inclusion wins when components of one feature disagree.
_INCLUSION_ORDER = ["always", "requested", "suggest", "only-if-asked"]


@dataclass(frozen=True)
class Feature:
    feature_id: str
    name: str
    component_ids: tuple[str, ...]
    inclusion: str                       # always | requested | suggest | only-if-asked
    site_role: str                       # section | global | page-layout | overlay
    pages: tuple[str, ...]               # first entry is the feature's main page
    content_needs: tuple[str, ...]
    business_types: tuple[str, ...]
    user_phrases: tuple[str, ...]
    not_for: tuple[tuple[str, str], ...]  # (feature_id, reason) that this feature is often confused with

    @property
    def main_page(self) -> str | None:
        """The page this feature adds, or None when it lives on every page."""
        return None if self.pages[0] == "all" else self.pages[0]


@dataclass(frozen=True)
class Capability:
    capability_id: str
    group: str                           # feature | integration
    phrases: tuple[str, ...]
    reason: str
    alternative_text: str
    alternative_feature_ids: tuple[str, ...]


@dataclass(frozen=True)
class Baseline:
    baseline_id: str
    label: str
    priority: int
    signal_features: tuple[str, ...]
    default_features: tuple[str, ...]
    default_pages: tuple[str, ...]


@dataclass(frozen=True)
class Catalogue:
    features: dict[str, Feature]
    capabilities: dict[str, Capability]
    baselines: tuple[Baseline, ...]      # sorted by priority
    page_kinds: tuple[str, ...]
    content_keys: tuple[str, ...]
    catalogue_hash: str
    unsupported_list_hash: str
    baselines_hash: str

    @property
    def version(self) -> str:
        return f"{self.catalogue_hash}.{self.unsupported_list_hash}.{self.baselines_hash}"

    def feature_summary(self) -> str:
        """Compact feature list for a model prompt: id, name and example user phrases."""
        lines = []
        for f in self.features.values():
            if f.inclusion == "always":
                continue  # layout parts are added by Planning, never requested
            phrases = "; ".join(f.user_phrases[:3])
            lines.append(f"- {f.feature_id}: {f.name} (e.g. {phrases})")
        return "\n".join(lines)

    def unsupported_summary(self) -> str:
        """Compact unsupported list for a model prompt."""
        return "\n".join(
            f"- {c.capability_id}: {', '.join(c.phrases[:4])}" for c in self.capabilities.values()
        )


def _read(path: Path) -> tuple[Any, str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()[:12]


def _build_features(components: list[dict[str, Any]]) -> dict[str, Feature]:
    component_to_feature = {c["component_id"]: c["featureId"] for c in components}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for c in components:
        grouped.setdefault(c["featureId"], []).append(c)

    features: dict[str, Feature] = {}
    for fid, comps in grouped.items():
        first = comps[0]
        not_for: dict[str, str] = {}
        for c in comps:
            for nf in c.get("notFor") or []:
                other = component_to_feature.get(nf["id"])
                if other and other != fid:
                    not_for.setdefault(other, nf["reason"])
        features[fid] = Feature(
            feature_id=fid,
            name=first["feature"],
            component_ids=tuple(c["component_id"] for c in comps),
            inclusion=min((c["inclusion"] for c in comps), key=_INCLUSION_ORDER.index),
            site_role=first["siteRole"],
            pages=tuple(first["pages"]),
            content_needs=tuple(sorted({k for c in comps for k in c["contentNeeds"]})),
            business_types=tuple(sorted({b for c in comps for b in c["businessTypes"]})),
            user_phrases=tuple(p for c in comps for p in c.get("userPhrases") or []),
            not_for=tuple(not_for.items()),
        )
    return features


@lru_cache(maxsize=1)
def load_catalogue() -> Catalogue:
    """Load and validate all catalogue files once per process."""
    components, catalogue_hash = _read(CATALOG_FILE)
    unsupported, unsupported_hash = _read(UNSUPPORTED_FILE)
    baselines_raw, baselines_hash = _read(BASELINES_FILE)

    features = _build_features(components)
    component_to_feature = {c["component_id"]: c["featureId"] for c in components}

    capabilities = {
        u["capability_id"]: Capability(
            capability_id=u["capability_id"],
            group=u["group"],
            phrases=tuple(u["phrases"]),
            reason=u["reason"],
            alternative_text=u.get("alternativeText", ""),
            alternative_feature_ids=tuple(
                dict.fromkeys(component_to_feature[c] for c in u.get("alternativeComponents", [])
                              if c in component_to_feature)
            ),
        )
        for u in unsupported
    }

    baselines = tuple(sorted(
        (Baseline(
            baseline_id=b["baseline_id"],
            label=b["label"],
            priority=b["priority"],
            signal_features=tuple(b["signal_features"]),
            default_features=tuple(b["default_features"]),
            default_pages=tuple(b["default_pages"]),
        ) for b in baselines_raw["baselines"]),
        key=lambda b: b.priority,
    ))

    page_kinds = tuple(sorted({p for c in components for p in c["pages"]} - {"all"}))
    content_keys = tuple(sorted({k for c in components for k in c["contentNeeds"]}))

    # Fail early if the data files disagree with each other.
    for b in baselines:
        unknown = [f for f in b.signal_features + b.default_features if f not in features]
        bad_pages = [p for p in b.default_pages if p not in page_kinds]
        if unknown or bad_pages:
            raise ValueError(f"site_baselines.json '{b.baseline_id}': unknown features {unknown}, pages {bad_pages}")

    return Catalogue(
        features=features,
        capabilities=capabilities,
        baselines=baselines,
        page_kinds=page_kinds,
        content_keys=content_keys,
        catalogue_hash=catalogue_hash,
        unsupported_list_hash=unsupported_hash,
        baselines_hash=baselines_hash,
    )
