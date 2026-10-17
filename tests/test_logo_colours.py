"""
Logo and screenshot colours (agents/logo_colours.py, D-163, D-164). Offline: test images are drawn
with Pillow in KNOWN colours, so we can measure whether the extractor gets them back.
"""
import io

import pytest
from PIL import Image, ImageDraw

from agents import theming
from agents.logo_colours import ImageError, logo_colours, screenshot_colours

MAX_DELTA_E = 10.0   # "the same colour" to the eye, after JPEG/quantizer rounding


def encode(image: Image.Image, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


def close(a: str, b: str) -> bool:
    return not theming.visibly_different(a, b) and _delta(a, b) <= MAX_DELTA_E


def _delta(a: str, b: str) -> float:
    la, lb = theming.lab_from_argb(theming._argb(a)), theming.lab_from_argb(theming._argb(b))
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5


@pytest.mark.parametrize("brand", ["#c0392b", "#1f4e9c", "#2e7d4f", "#f2a900", "#8e44ad"])
@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_one_colour_logo_on_white(brand, fmt):
    image = Image.new("RGB", (400, 300), "white")
    ImageDraw.Draw(image).ellipse((100, 50, 300, 250), fill=brand)
    result = logo_colours(encode(image, fmt))
    assert not result["monochrome"] and close(result["colours"][0], brand), result


def test_two_colour_transparent_logo_gives_both():
    image = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 180, 180), fill="#1f4e9c")
    draw.rectangle((150, 150, 280, 280), fill="#f2a900")
    colours = logo_colours(encode(image))["colours"]
    assert any(close(c, "#1f4e9c") for c in colours) and any(close(c, "#f2a900") for c in colours)


def test_logo_on_coloured_background_ignores_the_background():
    image = Image.new("RGB", (400, 300), "#f4efe6")            # cream background
    ImageDraw.Draw(image).rectangle((120, 80, 280, 220), fill="#c0392b")
    assert close(logo_colours(encode(image))["colours"][0], "#c0392b")


def test_black_and_white_logo_is_monochrome():
    image = Image.new("RGB", (300, 100), "white")
    ImageDraw.Draw(image).rectangle((20, 30, 280, 70), fill="black")
    assert logo_colours(encode(image)) == {"kind": "logo", "colours": [], "monochrome": True}


def test_light_screenshot():
    image = Image.new("RGB", (1280, 800), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1280, 90), fill="#1a7f5a")
    draw.rectangle((100, 200, 900, 220), fill="#333333")
    result = screenshot_colours(encode(image, "JPEG"))
    assert result["background"] == "#ffffff" and close(result["primary"], "#1a7f5a") and result["is_dark"] is False


def test_dark_screenshot():
    image = Image.new("RGB", (1280, 800), "#111418")
    ImageDraw.Draw(image).rectangle((100, 400, 300, 460), fill="#e4572e")
    result = screenshot_colours(encode(image))
    assert result["is_dark"] is True and close(result["primary"], "#e4572e")


@pytest.mark.parametrize("data, message", [
    (b"", "empty"),
    (b"not an image", "couldn't open"),
    (b"x" * (2 * 1024 * 1024 + 1), "larger than 2 MB"),
], ids=["empty", "not-an-image", "over-2MB"])
def test_bad_files_get_plain_messages(data, message):
    with pytest.raises(ImageError, match=message):
        logo_colours(data)


def test_unsupported_format_and_huge_dimensions():
    with pytest.raises(ImageError, match="PNG, JPG or WebP"):
        logo_colours(encode(Image.new("RGB", (10, 10)), "GIF"))
    huge = encode(Image.new("1", (6000, 6000)))                 # 36 M pixels, but a tiny file
    with pytest.raises(ImageError, match="too large"):
        logo_colours(huge)
