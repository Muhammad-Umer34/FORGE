"""
Theme generation (agents/theming.py, D-155 - D-161).

Offline tests prove the contrast guarantee over a hue grid and check the candidate rules.
The live evaluation (FORGE_LIVE_TESTS=1) compares this design with asking Gemini for hex colours
directly, and prints the numbers for the FYP report:

    FORGE_LIVE_TESTS=1 .venv/Scripts/python.exe -m pytest tests/test_theming.py -k live -s
"""
import os

import pytest

from agents import theming as t

HUE_STEP = 5   # 72 hues x 8 personalities x light/dark; the full 1-degree grid (2,880 themes) also passed on 2026-10-17


def test_hex_helpers():
    assert t.normalise_hex("#1A7F5A") == "#1a7f5a"
    assert t.normalise_hex("abc") == "#aabbcc"
    assert t.normalise_hex("green") is None and t.normalise_hex("#12345") is None
    assert t.find_hex("our brand green is #1a7f5a, thanks") == "#1a7f5a"
    assert t.find_hex("call 0300#1234567") is None and t.find_hex("no colour here") is None


def test_wcag_contrast_formula():
    assert round(t.contrast_ratio("#000000", "#ffffff"), 2) == 21.0
    assert t.contrast_ratio("#777777", "#777777") == 1.0
    assert round(t.contrast_ratio("#767676", "#ffffff"), 2) == 4.54   # the well-known AA grey


def test_presets_are_consistent():
    presets = t.load_presets()
    assert set(presets["personalities"]) == set(t.PERSONALITIES)
    assert set(presets["hue_families"]) == set(t.HUE_FAMILIES)
    assert all(len(c["hues"]) == 3 for c in presets["business_conventions"])


@pytest.mark.parametrize("personality", t.PERSONALITIES)
def test_every_theme_passes_wcag_aa_in_light_and_dark(personality):           # D-156
    preset = t.load_presets()["personalities"][personality]
    for hue in range(0, 360, HUE_STEP):
        seed = t._hex(t.Hct.from_hct(hue, 60, 50).to_int())
        theme = t.build_theme(t.ThemeParams(personality, seed, preset["variant"], preset["contrast_level"],
                                            t._font_pairs(personality)[0], preset["radius"]))
        for mode in ("light", "dark"):
            assert t.failing_pairs(theme["tokens"][mode]) == [], (personality, hue, mode)
        assert theme["contrast"]["min_text_ratio"] >= t.TEXT_CONTRAST


def test_brand_colours_that_are_hard_to_read_still_pass():
    for brand in ("#ffff00", "#00ffff", "#ff9900", "#ffffff", "#000000", "#777777"):   # yellow, cyan, orange, extremes
        theme = t.build_theme(t.ThemeParams("bold", brand, "fidelity", 0.0, "sora-inter", "0.5rem"))
        assert all(t.failing_pairs(theme["tokens"][m]) == [] for m in ("light", "dark")), brand


def test_contrast_fixer_repairs_a_broken_token_set():
    theme = t.build_theme(t.ThemeParams("calm", "#2563b8", "tonal_spot", 0.0, "inter", "0.5rem"))
    broken = dict(theme["tokens"]["light"], **{"muted-foreground": "#d0d0d0", "primary-foreground": "#3a3a3a"})
    assert t.failing_pairs(broken)
    assert t.enforce_contrast(broken) >= 2 and t.failing_pairs(broken) == []


def test_same_parameters_give_the_same_theme():
    params = t.ThemeParams("warm", "#c88a12", "tonal_spot", 0.0, "nunito", "0.75rem")
    t.build_theme.cache_clear()
    first = t.build_theme(params)
    t.build_theme.cache_clear()
    assert t.build_theme(params) == first


def _primary_hue(theme: dict) -> float:
    return t.Hct.from_int(t._argb(theme["tokens"]["light"]["primary"])).hue


@pytest.mark.parametrize("business", [c["keywords"][0] for c in t.load_presets()["business_conventions"]] + [None])
def test_three_distinct_candidates_one_selected(business):                     # D-157
    themes = t.candidates(business)
    assert len(themes) == 3 and len({th["theme_id"] for th in themes}) == 3
    assert sum(th["selected"] for th in themes) == 1 and themes[0]["selected"]
    a, b, c = (th["tokens"]["light"]["primary"] for th in themes)
    assert t.visibly_different(a, b) and t.visibly_different(a, c) and t.visibly_different(b, c), (a, b, c)
    assert "Purple" not in " ".join(th["label"] for th in themes)             # avoided unless asked


def test_user_choices_shape_the_candidates():
    stated = t.candidates("bakery", personality="elegant", hue_family="purple")
    assert stated[0]["label"] == "Elegant · Purple" and stated[0]["reason"] == "What you described"
    branded = t.candidates("law firm", brand_colour="#1A7F5A")
    assert branded[2]["kind"] == "brand" and branded[2]["selected"] and not branded[0]["selected"]
    assert branded[2]["params"]["seed_hex"] == "#1a7f5a" and branded[2]["params"]["variant"] == "fidelity"


# ---------------------------------------------------------------- live evaluation (costs Gemini credits)
live = pytest.mark.skipif(os.getenv("FORGE_LIVE_TESTS") != "1", reason="set FORGE_LIVE_TESTS=1 to call Gemini")

EVAL_BUSINESSES = ["bakery", "dental clinic", "law firm", "gym", "hair salon", "photography studio",
                   "florist", "coffee shop", "tutoring academy", "real estate agency"]


@live
def test_live_direct_llm_hex_vs_parameters_plus_code():
    """FYP evaluation (D-160): WCAG pass rate of model-written hex palettes vs this design."""
    from pydantic import BaseModel, Field

    from agents.gateway import call_structured

    class DirectPalette(BaseModel):
        tokens: dict[str, str] = Field(description="Hex colour for every token name listed, e.g. '#1a7f5a'.")

    names = sorted(t._ROLES) + ["success", "success-foreground"]
    direct_pass = direct_invalid = 0
    hues = []
    for business in EVAL_BUSINESSES:
        out, _ = call_structured(
            "clarification", DirectPalette,
            "You are a web designer. Return a light-mode colour theme as hex values.",
            f"Theme for a {business} website. Token names: {', '.join(names)}.",
        )
        tokens = {k: t.normalise_hex(out.tokens.get(k)) for k in names}
        if any(v is None for v in tokens.values()):
            direct_invalid += 1
            continue
        direct_pass += not t.failing_pairs(tokens)
        hues.append(round(t.Hct.from_int(t._argb(tokens["primary"])).hue))

    ours = [t.candidates(b)[0] for b in EVAL_BUSINESSES]
    ours_pass = sum(not t.failing_pairs(th["tokens"][m]) for th in ours for m in ("light", "dark"))
    print(f"\nDirect LLM hex: {direct_pass}/{len(EVAL_BUSINESSES)} pass WCAG AA, {direct_invalid} invalid, primary hues {hues}")
    print(f"Parameters + code: {ours_pass}/{2 * len(EVAL_BUSINESSES)} pass (light and dark)")
    assert ours_pass == 2 * len(EVAL_BUSINESSES)
