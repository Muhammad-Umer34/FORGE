# D:\FYP\FORGE-1\agents\theming.py
"""
Theme generation (decisions D-155 - D-160). A theme is a small set of PARAMETERS
(personality, seed colour, scheme variant, contrast level, font pair, radius), never a hand-made
palette and never colours written by a model. Code turns the parameters into every colour token
the component library uses (shadcn/ui names), for light and dark mode, using Material's HCT colour
system (materialyoucolor, 2021 colour spec), then checks every text/background pair against
WCAG 2.2 AA and nudges the text colour's tone until it passes. Same parameters, same theme.

Business-type defaults come from components/theme_presets.json and are industry convention
(evidence grade C), so the user always chooses between three candidates.
"""
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache

from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors as M
from materialyoucolor.hct import Hct
from materialyoucolor.palettes.tonal_palette import TonalPalette
from materialyoucolor.scheme.scheme_content import SchemeContent
from materialyoucolor.scheme.scheme_expressive import SchemeExpressive
from materialyoucolor.scheme.scheme_fidelity import SchemeFidelity
from materialyoucolor.scheme.scheme_neutral import SchemeNeutral
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
from materialyoucolor.scheme.scheme_vibrant import SchemeVibrant
from materialyoucolor.utils.color_utils import lab_from_argb

from agents.catalogue import COMPONENTS_DIR

PRESETS_FILE = COMPONENTS_DIR / "theme_presets.json"
SPEC_VERSION = "2021"           # tone rules documented in the research (primary 40/80, on-primary 100/20)
TEXT_CONTRAST = 4.5             # WCAG 2.2 SC 1.4.3, normal text
UI_CONTRAST = 3.0               # WCAG 2.2 SC 1.4.11, UI components and focus indicators
SUCCESS_HUE, SUCCESS_CHROMA = 145.0, 40.0

VARIANTS = {
    "tonal_spot": SchemeTonalSpot,
    "vibrant": SchemeVibrant,
    "expressive": SchemeExpressive,
    "fidelity": SchemeFidelity,     # keeps a brand colour close to what the user gave
    "content": SchemeContent,
    "neutral": SchemeNeutral,
}

# shadcn token -> Material role, for light and dark.
_ROLES = {
    "background": (M.surface, M.surface),
    "foreground": (M.onSurface, M.onSurface),
    "card": (M.surfaceContainerLowest, M.surfaceContainerLow),
    "card-foreground": (M.onSurface, M.onSurface),
    "popover": (M.surfaceContainerLowest, M.surfaceContainerHigh),
    "popover-foreground": (M.onSurface, M.onSurface),
    "primary": (M.primary, M.primary),
    "primary-foreground": (M.onPrimary, M.onPrimary),
    "secondary": (M.secondaryContainer, M.secondaryContainer),
    "secondary-foreground": (M.onSecondaryContainer, M.onSecondaryContainer),
    "muted": (M.surfaceContainerHigh, M.surfaceContainerHighest),
    "muted-foreground": (M.onSurfaceVariant, M.onSurfaceVariant),
    "accent": (M.tertiaryContainer, M.tertiaryContainer),
    "accent-foreground": (M.onTertiaryContainer, M.onTertiaryContainer),
    "destructive": (M.error, M.error),
    "destructive-foreground": (M.onError, M.onError),
    "border": (M.outlineVariant, M.outlineVariant),   # decorative separators
    "input": (M.outline, M.outline),                  # form borders: must reach 3:1
    "ring": (M.primary, M.primary),
}

# (foreground, background, minimum ratio). Checked in this order; primary first because other pairs use it.
CONTRAST_PAIRS = [
    ("foreground", "background", TEXT_CONTRAST),
    ("primary", "background", TEXT_CONTRAST),          # text-primary is used on page backgrounds
    ("primary", "card", TEXT_CONTRAST),
    ("primary-foreground", "primary", TEXT_CONTRAST),
    ("card-foreground", "card", TEXT_CONTRAST),
    ("popover-foreground", "popover", TEXT_CONTRAST),
    ("foreground", "muted", TEXT_CONTRAST),
    ("secondary-foreground", "secondary", TEXT_CONTRAST),
    ("muted-foreground", "background", TEXT_CONTRAST),
    ("muted-foreground", "card", TEXT_CONTRAST),
    ("muted-foreground", "muted", TEXT_CONTRAST),
    ("accent-foreground", "accent", TEXT_CONTRAST),
    ("destructive", "background", TEXT_CONTRAST),
    ("destructive-foreground", "destructive", TEXT_CONTRAST),
    ("success", "background", TEXT_CONTRAST),
    ("success-foreground", "success", TEXT_CONTRAST),
    ("input", "background", UI_CONTRAST),
    ("ring", "background", UI_CONTRAST),
]

_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# ---------------------------------------------------------------- colour maths
def normalise_hex(value: str | None) -> str | None:
    """'#1A7F5A', '1a7f5a' or '#abc' -> '#1a7f5a'. Anything else -> None."""
    if not value:
        return None
    match = _HEX.match(value.strip())
    if not match:
        return None
    digits = match.group(1).lower()
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits}"


_HEX_IN_TEXT = re.compile(r"(?<![0-9a-zA-Z])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z])")


def find_hex(text: str) -> str | None:
    """The first hex colour written in the user's text, e.g. 'our green is #1a7f5a' -> '#1a7f5a'."""
    match = _HEX_IN_TEXT.search(text or "")
    return normalise_hex(match.group(0)) if match else None


def _hex(argb: int) -> str:
    return f"#{argb & 0xFFFFFF:06x}"


def _argb(hex_colour: str) -> int:
    return 0xFF000000 | int(hex_colour[1:], 16)


def _luminance(hex_colour: str) -> float:
    """WCAG 2.x relative luminance."""
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _adjust_until(fg: str, bg: str, target: float) -> str:
    """Move the foreground's HCT tone away from the background (hue and chroma kept) until it passes."""
    hct = Hct.from_int(_argb(fg))
    darker = _luminance(bg) > 0.18          # light background: text gets darker
    tone = hct.tone
    while 0 <= tone <= 100:
        tone += -1 if darker else 1
        candidate = _hex(Hct.from_hct(hct.hue, hct.chroma, max(0.0, min(100.0, tone))).to_int())
        if contrast_ratio(candidate, bg) >= target:
            return candidate
    black_or_white = "#000000" if darker else "#ffffff"
    return black_or_white


def enforce_contrast(tokens: dict[str, str]) -> int:
    """Fix every failing pair in place. Returns how many colours were changed."""
    fixes = 0
    for _ in range(3):                       # later fixes can affect earlier pairs (primary is shared)
        changed = False
        for fg, bg, target in CONTRAST_PAIRS:
            if contrast_ratio(tokens[fg], tokens[bg]) < target:
                tokens[fg] = _adjust_until(tokens[fg], tokens[bg], target)
                fixes += 1
                changed = True
        if not changed:
            break
    return fixes


def luminance(hex_colour: str) -> float:
    """WCAG relative luminance (0 = black, 1 = white)."""
    return _luminance(hex_colour)


def chroma_of(hex_colour: str) -> float:
    """How colourful a colour is (HCT chroma): about 0 for greys, 40+ for clear brand colours."""
    return Hct.from_int(_argb(hex_colour)).chroma


# ---------------------------------------------------------------- fonts from another website (Phase 2, D-167)
_SERIF_FONTS = {
    "georgia", "times", "times new roman", "garamond", "eb garamond", "playfair display", "merriweather", "lora",
    "libre baskerville", "cormorant garamond", "cormorant", "crimson pro", "crimson text", "fraunces", "dm serif display",
    "instrument serif", "pt serif", "source serif 4", "source serif pro", "noto serif", "roboto slab", "bitter",
    "libre caslon text", "spectral", "baskerville", "cambria", "book antiqua", "palatino", "palatino linotype",
}
_GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif",
            "ui-monospace", "-apple-system", "blinkmacsystemfont", "emoji", "math"}


def _families(stack: str) -> list[str]:
    return [f.strip().strip("'\"").lower() for f in stack.split(",") if f.strip()]


def first_font(stack: str) -> str:
    """The first named font in a CSS font-family list, as written ('"Playfair Display", serif' -> 'Playfair Display')."""
    for family in stack.split(","):
        name = family.strip().strip("'\"")
        if name and name.lower() not in _GENERIC:
            return name
    return ""


def font_class(stack: str) -> str:
    """'serif' or 'sans' for a CSS font-family list (monospace counts as sans for our pairs)."""
    families = _families(stack)
    named = [f for f in families if f not in _GENERIC]
    if named and named[0] in _SERIF_FONTS:
        return "serif"
    if "serif" in families and not named:
        return "serif"
    if named and "serif" in families and "sans-serif" not in families:
        return "serif"
    return "sans"


def closest_font_pair(heading_stack: str, body_stack: str) -> tuple[str, bool]:
    """
    Our font pair that best matches another site's fonts: the exact heading font if we have it,
    else a pair with the same kind of heading and body font (serif / sans). Returns (pair_id, exact).
    Paid or custom fonts can't be shipped, so a close free Google Font is used instead.
    """
    pairs = load_presets()["font_pairs"]
    # 'Inter Variable', 'Inter VF', 'inter-var' are the same typeface as 'Inter'.
    clean = lambda name: re.sub(r"[\s-]+(variable|vf|var)$", "", name.lower()).strip()
    heading, body = clean(first_font(heading_stack)), clean(first_font(body_stack))
    for p in pairs:
        if heading and p["heading"].lower() == heading and p["body"].lower() == body:
            return p["id"], True
    for p in pairs:
        if heading and p["heading"].lower() == heading:
            return p["id"], True
    h_class, b_class = font_class(heading_stack), font_class(body_stack or heading_stack)

    def kind(name: str) -> str:
        return "serif" if name.lower() in _SERIF_FONTS else "sans"

    same_kind = [p for p in pairs if kind(p["heading"]) == h_class and kind(p["body"]) == b_class]
    same_kind.sort(key=lambda p: p["body"].lower() != body)          # prefer our pair that shares their body font
    choice = same_kind[0] if same_kind else next(p for p in pairs if kind(p["heading"]) == h_class)
    return choice["id"], False


def failing_pairs(tokens: dict[str, str]) -> list[str]:
    return [f"{fg} on {bg}: {contrast_ratio(tokens[fg], tokens[bg]):.2f} < {t}"
            for fg, bg, t in CONTRAST_PAIRS if contrast_ratio(tokens[fg], tokens[bg]) < t]


# ---------------------------------------------------------------- presets
@lru_cache(maxsize=1)
def load_presets() -> dict:
    presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    pair_ids = {p["id"] for p in presets["font_pairs"]}
    for name, p in presets["personalities"].items():
        if p["variant"] not in VARIANTS:
            raise ValueError(f"theme_presets.json: unknown variant for {name}")
        if not any(set(p["font_tags"]) & set(fp["tags"]) for fp in presets["font_pairs"]):
            raise ValueError(f"theme_presets.json: no font pair for {name}")
    for conv in presets["business_conventions"] + [presets["default_convention"]]:
        if conv["personality"] not in presets["personalities"] or any(h not in presets["hue_families"] for h in conv["hues"]):
            raise ValueError(f"theme_presets.json: bad convention {conv}")
    assert len(pair_ids) == len(presets["font_pairs"]), "duplicate font pair ids"
    return presets


PERSONALITIES = ("professional", "calm", "warm", "bold", "elegant", "playful", "natural", "minimal")
HUE_FAMILIES = ("red", "orange", "amber", "brown", "olive", "green", "teal", "blue", "navy", "purple", "pink", "charcoal")


# ---------------------------------------------------------------- one theme
@dataclass(frozen=True)
class ThemeParams:
    personality: str
    seed_hex: str
    variant: str
    contrast_level: float
    font_pair_id: str
    radius: str
    hue_family: str | None = None     # None when the seed is the user's own colour


def _tokens(params: ThemeParams, dark: bool) -> dict[str, str]:
    scheme = VARIANTS[params.variant](Hct.from_int(_argb(params.seed_hex)), dark, params.contrast_level,
                                      spec_version=SPEC_VERSION)
    tokens = {name: _hex(role[1 if dark else 0].get_argb(scheme)) for name, role in _ROLES.items()}
    success = TonalPalette.from_hue_and_chroma(SUCCESS_HUE, SUCCESS_CHROMA)
    tokens["success"] = _hex(success.tone(80 if dark else 40))
    tokens["success-foreground"] = _hex(success.tone(20 if dark else 100))
    return tokens


@lru_cache(maxsize=512)
def build_theme(params: ThemeParams) -> dict:
    """Full theme: parameters, fonts, radius and contrast-checked tokens for light and dark."""
    pair = next(p for p in load_presets()["font_pairs"] if p["id"] == params.font_pair_id)
    light, dark = _tokens(params, dark=False), _tokens(params, dark=True)
    fixes = enforce_contrast(light) + enforce_contrast(dark)
    ratios = [contrast_ratio(t[fg], t[bg]) for t in (light, dark) for fg, bg, target in CONTRAST_PAIRS if target == TEXT_CONTRAST]
    key = json.dumps(asdict(params), sort_keys=True)
    return {
        "theme_id": "t-" + hashlib.sha256(key.encode()).hexdigest()[:10],
        "params": asdict(params),
        "fonts": {"heading": pair["heading"], "body": pair["body"]},
        "radius": params.radius,
        "tokens": {"light": light, "dark": dark},
        "contrast": {"standard": "WCAG 2.2 AA", "min_text_ratio": round(min(ratios), 2), "fixes": fixes},
    }


# ---------------------------------------------------------------- three candidates
def convention_for(business_type: str | None) -> dict:
    presets = load_presets()
    text = (business_type or "").lower()
    for conv in presets["business_conventions"]:
        if any(k in text for k in conv["keywords"]):
            return conv
    return presets["default_convention"]


def _font_pairs(personality: str) -> list[str]:
    tags = set(load_presets()["personalities"][personality]["font_tags"])
    return [p["id"] for p in load_presets()["font_pairs"] if tags & set(p["tags"])]


ACHROMATIC = {"charcoal"}      # grey families keep a low-colour scheme; other variants would tint them blue
MIN_HUE_GAP = 35.0             # degrees between the 'match' and 'alternative' colours, so they look different
MIN_VISIBLE_DELTA_E = 15.0     # CIE76 distance between candidate primaries: clearly different to the eye (D-162)


def visibly_different(a: str, b: str) -> bool:
    la, lb = lab_from_argb(_argb(a)), lab_from_argb(_argb(b))
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5 >= MIN_VISIBLE_DELTA_E


def _hue_of(family: str) -> float:
    return Hct.from_int(_argb(load_presets()["hue_families"][family]["seed"])).hue


def _distinct(a: str, b: str) -> bool:
    if (a in ACHROMATIC) != (b in ACHROMATIC):
        return True
    if a in ACHROMATIC:
        return a != b
    gap = abs(_hue_of(a) - _hue_of(b)) % 360
    return min(gap, 360 - gap) >= MIN_HUE_GAP


def _params(personality: str, hue: str | None, seed: str | None, font_index: int, variant: str | None = None) -> ThemeParams:
    preset = load_presets()["personalities"][personality]
    pairs = _font_pairs(personality)
    if hue in ACHROMATIC and not variant:
        variant = "neutral"
    return ThemeParams(
        personality=personality,
        seed_hex=seed or load_presets()["hue_families"][hue]["seed"],
        variant=variant or preset["variant"],
        contrast_level=preset["contrast_level"],
        font_pair_id=pairs[font_index % len(pairs)],
        radius=preset["radius"],
        hue_family=hue if not seed else None,
    )


def _label(personality: str, hue: str | None) -> str:
    presets = load_presets()
    name = presets["personalities"][personality]["label"]
    return f"{name} · {presets['hue_families'][hue]['label']}" if hue else name


def _source_theme(feel: str, hue_order: list[str], brand: str | None, logo_colour: str | None,
                  screenshot: dict | None, reference: dict | None, prefers_dark: bool):
    """
    The theme built from the user's own material (Phase 2, D-168), or None when there is none.
    Colour priority: logo > typed hex > website > screenshot. Fonts and corners come from the website.
    """
    logo = normalise_hex(logo_colour)
    shot = screenshot or {}
    if not (logo or brand or shot or reference):
        return None
    ref = reference or {}
    seed = logo or brand or normalise_hex(ref.get("primary")) or normalise_hex(shot.get("primary"))
    personality = ref.get("personality") if ref.get("personality") in PERSONALITIES else feel
    preset = load_presets()["personalities"][personality]
    font = ref.get("font_pair_id") or _font_pairs(personality)[2 % len(_font_pairs(personality))]
    radius = ref.get("radius") or preset["radius"]
    if seed:
        params = ThemeParams(personality, seed, "fidelity", preset["contrast_level"], font, radius)
    else:     # a site with no clear brand colour: its fonts and corners with a colour that suits the business
        base = _params(personality, hue_order[0], None, 0)
        params = ThemeParams(personality, base.seed_hex, base.variant, base.contrast_level, font, radius, hue_order[0])
    dark = bool(ref.get("is_dark") or shot.get("is_dark") or prefers_dark)
    host = ref.get("host")
    if logo and host:
        meta = ("combined", f"Your logo colour, styled like {host}", "Colours from your logo, fonts and corners from the site")
    elif host:
        meta = ("reference", f"Inspired by {host}", "Colours, fonts and corners from the site")
    elif logo:
        meta = ("logo", "Your logo colour", f"Taken from your logo ({logo})")
    elif shot:
        meta = ("screenshot", "From your screenshot", "Colours taken from the screenshot")
    else:
        meta = ("brand", f"Your colour {brand}", "Built from the colour you gave")
    return params, meta, dark


def candidates(business_type: str | None, personality: str | None = None, hue_family: str | None = None,
               brand_colour: str | None = None, prefers_dark: bool = False, logo_colour: str | None = None,
               screenshot: dict | None = None, reference: dict | None = None) -> list[dict]:
    """
    Three themes for the confirmation screen (D-157):
      1. 'match'      - what the user asked for, else the convention for their kind of business
      2. 'alternative'- the same feel in a different colour and font pair
      3. the user's own material when there is any (typed hex, logo, screenshot or a website - D-168),
         otherwise a contrasting feel
    Exactly one is marked selected: the user's own material when given, otherwise 'match'.
    """
    presets = load_presets()
    conv = convention_for(business_type)
    avoid = set(presets["avoid_unless_asked"]) - ({hue_family} if hue_family else set())
    feel = personality if personality in presets["personalities"] else conv["personality"]
    stated_hue = hue_family if hue_family in presets["hue_families"] else None
    hue_order = [h for h in ([stated_hue] if stated_hue else []) + conv["hues"] + list(HUE_FAMILIES) if h and h not in avoid]
    hue_order = list(dict.fromkeys(hue_order))
    reason_conv = f"Common for a {business_type}" if business_type else "A safe, popular choice"

    first = _params(feel, hue_order[0], None, 0)
    first_primary = build_theme(first)["tokens"]["light"]["primary"]
    second_hue = next((h for h in hue_order[1:] if _distinct(hue_order[0], h)
                       and visibly_different(first_primary, build_theme(_params(feel, h, None, 1))["tokens"]["light"]["primary"])),
                      None)
    if second_hue:
        second = _params(feel, second_hue, None, 1)
    else:   # a grey style mutes every colour alike: show the next colour at normal strength instead
        second_hue = next(h for h in hue_order[1:] if _distinct(hue_order[0], h))
        second = _params(feel, second_hue, None, 1, variant="tonal_spot")
    brand = normalise_hex(brand_colour)
    source = _source_theme(feel, hue_order, brand, logo_colour, screenshot, reference, prefers_dark)
    if source:
        third, third_meta, source_dark = source
    else:
        other_feel = "calm" if feel == "bold" else "bold"
        # A grey first theme would stay grey in any feel, so the contrasting look takes the other colour.
        third_hue = second_hue if hue_order[0] in ACHROMATIC else hue_order[0]
        third = _params(other_feel, third_hue, None, 0)
        # Some colours look the same in both feels; then the contrasting look also changes colour.
        taken = [first_primary, build_theme(second)["tokens"]["light"]["primary"]]
        for hue in [third_hue] + [h for h in hue_order if h not in (hue_order[0], second_hue)]:
            third = _params(other_feel, hue, None, 0)
            if all(visibly_different(build_theme(third)["tokens"]["light"]["primary"], p) for p in taken):
                third_hue = hue
                break
        third_meta = ("contrast", _label(other_feel, third_hue), f"A {'calmer' if other_feel == 'calm' else 'bolder'} look")

    stated = bool(personality or stated_hue)
    rows = [
        ("match", first, _label(feel, hue_order[0]), "What you described" if stated else reason_conv),
        ("alternative", second, _label(feel, second_hue), "Same feel, different colour"),
        (third_meta[0], third, third_meta[1], third_meta[2]),
    ]
    result = []
    for index, (kind, params, label, reason) in enumerate(rows):
        theme = dict(build_theme(params))
        dark = source_dark if (source and index == 2) else prefers_dark
        theme.update(kind=kind, label=label, reason=reason, selected=(index == 2) if source else (kind == "match"),
                     default_mode="dark" if dark else "light")
        if source and index == 2 and reference:
            theme["notes"] = list(reference.get("notes") or [])
        result.append(theme)
    return result
