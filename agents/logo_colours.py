# D:\FYP\FORGE-1\agents\logo_colours.py
"""
Colours from an uploaded logo or website screenshot (theme Phase 2, decisions D-163, D-164).

Local code only: Pillow opens the image in memory and Material's quantizer (Wu + k-means,
"QuantizeCelebi") and Score pick the main colours - the method Android uses to take theme colours
from a wallpaper. No model call, no outside service, and the image is never written to disk or
put into the LangGraph state: only the chosen hex colour is.

Logo:       drop transparent, near-white, near-black and border-background pixels -> up to 4 brand colours.
Screenshot: keep everything -> page background, main colour (most vivid common colour), light or dark.
"""
import io
from collections import Counter

from materialyoucolor.quantize import QuantizeCelebi
from materialyoucolor.score.score import Score, ScoreOptions
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 2 * 1024 * 1024       # 2 MB upload limit
MAX_PIXELS = 25_000_000           # refuse decompression bombs before decoding
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
SAMPLE_SIZE = 128                 # images are shrunk to at most 128 x 128 before counting colours
MAX_COLOURS = 4
_NO_COLOUR = 0                    # Score fallback sentinel: "nothing usable found"


class ImageError(ValueError):
    """A problem with the uploaded image, worded for the user."""


def _hex(argb: int) -> str:
    return f"#{argb & 0xFFFFFF:06x}"


def _luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _open(data: bytes) -> Image.Image:
    if not data:
        raise ImageError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise ImageError("The image is larger than 2 MB. Please upload a smaller PNG, JPG or WebP file.")
    try:
        image = Image.open(io.BytesIO(data))
        if image.format not in ALLOWED_FORMATS:
            raise ImageError("Please upload a PNG, JPG or WebP image.")
        if image.width * image.height > MAX_PIXELS:
            raise ImageError("The image is too large to read. Please upload a smaller version.")
        image.thumbnail((SAMPLE_SIZE, SAMPLE_SIZE))
        return image.convert("RGBA")
    except ImageError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ImageError("We couldn't open that image. Please upload a PNG, JPG or WebP file.")


def _near(a: tuple, b: tuple, tolerance: int = 24) -> bool:
    return all(abs(x - y) <= tolerance for x, y in zip(a[:3], b[:3]))


def _border_colour(image: Image.Image) -> tuple | None:
    """The colour that fills most of the image's edge, if one clearly does (a logo's background)."""
    w, h = image.size
    px = image.load()
    edge = [px[x, y] for x in range(w) for y in (0, h - 1)] + [px[x, y] for y in range(h) for x in (0, w - 1)]
    edge = [p for p in edge if p[3] >= 128]
    if not edge:
        return None
    rounded = Counter((p[0] // 16, p[1] // 16, p[2] // 16) for p in edge)
    (key, count), = rounded.most_common(1)
    if count < 0.4 * len(edge):
        return None
    return tuple(min(255, v * 16 + 8) for v in key)


def _ranked(population: dict[int, int]) -> list[str]:
    if not population:
        return []
    ranked = Score.score(population, ScoreOptions(desired=MAX_COLOURS, fallback_color_argb=_NO_COLOUR, filter=True))
    return [_hex(c) for c in ranked if c != _NO_COLOUR]


def logo_colours(data: bytes) -> dict:
    """Up to 4 brand colours, most likely first. monochrome=True when the logo has no real colour."""
    image = _open(data)
    opaque = [p for p in image.get_flattened_data() if p[3] >= 128]
    if not opaque:
        raise ImageError("The logo looks empty or fully transparent.")
    border = _border_colour(image)
    keep = [
        p for p in opaque
        if min(p[:3]) <= 235            # not near-white
        and max(p[:3]) >= 25            # not near-black
        and not (border and _near(p, border))
    ]
    colours = _ranked(QuantizeCelebi([[r, g, b, 255] for r, g, b, _ in keep], 64)) if keep else []
    return {"kind": "logo", "colours": colours, "monochrome": not colours}


def screenshot_colours(data: bytes) -> dict:
    """Background, main colour and light/dark from a screenshot of a website the user likes."""
    image = _open(data)
    pixels = [[r, g, b, 255] for r, g, b, a in image.get_flattened_data() if a >= 128]
    if not pixels:
        raise ImageError("The screenshot looks empty.")
    population = QuantizeCelebi(pixels, 32)
    background = max(population, key=population.get)
    colours = _ranked({c: n for c, n in population.items() if c != background})
    bg_rgb = ((background >> 16) & 255, (background >> 8) & 255, background & 255)
    return {
        "kind": "screenshot",
        "background": _hex(background),
        "colours": colours,
        "primary": colours[0] if colours else None,
        "is_dark": _luminance(bg_rgb) < 0.2,
    }
