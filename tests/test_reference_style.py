"""
"Make it look like this website" (agents/reference_style.py, D-165 - D-168).

Offline: address safety rules (DNS answers are faked, so no network), style summaries from raw
styles, font matching, and reading HTML loaded straight into the browser (nothing is fetched).
Live (FORGE_LIVE_TESTS=1): real small-business-style websites, reporting success rate and time:

    FORGE_LIVE_TESTS=1 .venv/Scripts/python.exe -m pytest tests/test_reference_style.py -k live -s
"""
import os
import socket
import time

import pytest

from agents import reference_style as rs
from agents import theming

FAKE_DNS = {
    "public-shop.com": "93.184.216.34",
    "evil-rebind.com": "127.0.0.1",          # a public name that points inside the server
    "metadata-trick.com": "169.254.169.254",
    "intranet.com": "10.1.2.3",
}


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    def getaddrinfo(host, *args, **kwargs):
        if host not in FAKE_DNS:
            raise socket.gaierror("not found")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (FAKE_DNS[host], 0))]
    monkeypatch.setattr(rs.socket, "getaddrinfo", getaddrinfo)
    yield


@pytest.mark.parametrize("url", ["https://public-shop.com", "http://public-shop.com/menu?x=1", "https://public-shop.com:443/"])
def test_public_addresses_are_allowed(url):
    assert rs.check_url(url) == url


@pytest.mark.parametrize("url", [
    "http://localhost", "http://127.0.0.1", "http://10.0.0.5", "http://192.168.1.1", "http://172.16.0.1",
    "http://169.254.169.254/latest/meta-data", "http://[::1]/", "http://100.64.0.1",          # carrier NAT
    "https://evil-rebind.com", "https://metadata-trick.com", "https://intranet.com",          # names pointing inside
    "file:///etc/passwd", "ftp://public-shop.com", "javascript:alert(1)",
    "https://public-shop.com:8080", "https://user:pw@public-shop.com", "http://printer.local",
    "http://router.lan", "https://unknown-site-xyz.com", "https://",
])
def test_unsafe_or_unknown_addresses_are_blocked(url):
    with pytest.raises(rs.ReferenceSiteError):
        rs.check_url(url)


def test_find_url_in_the_request():
    assert rs.find_url("make it look like www.stripe.com please") == "www.stripe.com"
    assert rs.find_url("like https://linear.app/features.") == "https://linear.app/features"
    assert rs.find_url("similar to apple.com") == "apple.com"
    assert rs.find_url("a bakery website with a menu") is None
    assert rs.normalise_url("www.x.com") == "https://www.x.com"


def test_font_matching():
    assert theming.closest_font_pair('"Playfair Display", serif', "Inter") == ("playfair-source", True)
    assert theming.closest_font_pair('"Inter Variable", sans-serif', "Inter") == ("inter", True)
    pair, exact = theming.closest_font_pair('"Tiempos Headline", Georgia, serif', "Graphik, sans-serif")
    assert not exact and theming.font_class('"Tiempos Headline", Georgia, serif') == "serif"
    assert pair in {p["id"] for p in theming.load_presets()["font_pairs"]}


RAW = {
    "background": [255, 250, 243, 255], "text": [43, 33, 24, 255],
    "heading_font": '"Playfair Display", serif', "body_font": "Lato, sans-serif",
    "buttons": [{"bg": [183, 75, 33, 255], "radius": 999, "height": 42, "area": 5000},
                {"bg": [0, 0, 0, 0], "radius": 0, "height": 30, "area": 900}],          # a transparent text button
    "links": [[183, 75, 33, 255], [43, 33, 24, 255]], "header_bg": [255, 250, 243, 255],
}


def test_summary_from_raw_styles():
    s = rs.summarise(RAW, "https://www.public-shop.com/")
    assert s["host"] == "public-shop.com" and s["background"] == "#fffaf3"
    assert s["primary"] == "#b74b21" and s["is_dark"] is False
    assert s["radius"] == "1rem" and s["font_pair_id"] == "playfair-source" and s["fonts_exact"]
    assert s["personality"] == "elegant" and s["notes"] == []


def test_summary_without_brand_colour_on_a_dark_site():
    raw = dict(RAW, background=[8, 9, 10, 255], buttons=[], links=[[230, 230, 230, 255]],
               heading_font="Circular, sans-serif", body_font="Circular, sans-serif")
    s = rs.summarise(raw, "https://public-shop.com")
    assert s["primary"] is None and s["is_dark"] is True
    assert any("No clear brand colour" in n for n in s["notes"]) and any("Circular" in n for n in s["notes"])


def _browser_available() -> bool:
    try:
        rs.read_in_process("https://public-shop.com", html="<p>x</p>")
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _browser_available(), reason="Chromium not installed: python -m playwright install chromium")
def test_reading_html_in_the_browser_handles_modern_colour_formats():
    html = """<html><head><style>
      body{background:#fffaf3;color:#2b2118;font-family:Lato,sans-serif}
      h1{font-family:'Playfair Display',serif}
      .btn{background:oklch(0.55 0.15 40);border-radius:999px;padding:12px 24px;display:inline-block}
      a{color:#b35a1f}</style></head>
      <body><header><a href='#'>Home</a></header><h1>Fresh bread</h1><a class='btn' href='#'>Order</a>
      <img src='http://127.0.0.1:8000/secret.png'></body></html>"""
    s = rs.summarise(rs.read_in_process("https://public-shop.com", html=html), "https://public-shop.com")
    assert s["background"] == "#fffaf3" and s["primary"] and theming.chroma_of(s["primary"]) > 16
    assert s["radius"] == "1rem" and s["font_pair_id"] == "playfair-source"


# ---------------------------------------------------------------- live (real websites, no model calls)
live = pytest.mark.skipif(os.getenv("FORGE_LIVE_TESTS") != "1", reason="set FORGE_LIVE_TESTS=1 to open real websites")

LIVE_SITES = [
    "https://www.airbnb.com", "https://stripe.com", "https://linear.app", "https://www.shopify.com",
    "https://www.squarespace.com", "https://www.wix.com", "https://www.mailchimp.com", "https://www.canva.com",
    "https://www.notion.so", "https://www.figma.com", "https://www.spotify.com", "https://www.duolingo.com",
    "https://www.etsy.com", "https://www.bbc.com", "https://www.ikea.com",
]


@live
def test_live_reference_sites(monkeypatch):
    monkeypatch.undo()                     # real DNS for live sites
    ok, times = 0, []
    for url in LIVE_SITES:
        started = time.time()
        try:
            s = rs.read_reference(url)
            ok += 1
            print(f"OK   {url:32} {time.time() - started:5.1f}s primary={s['primary']} dark={s['is_dark']} "
                  f"radius={s['radius']} font={s['heading_font_source']!r}->{s['font_pair_id']} feel={s['personality']}")
        except rs.ReferenceSiteError as error:
            print(f"FAIL {url:32} {time.time() - started:5.1f}s {error}")
        times.append(time.time() - started)
    print(f"\nRead {ok}/{len(LIVE_SITES)} sites; median time {sorted(times)[len(times) // 2]:.1f}s, max {max(times):.1f}s")
    assert ok >= len(LIVE_SITES) * 0.6


def test_browser_is_pinned_to_the_checked_address(fake_dns):
    assert rs._pin_rule("https://public-shop.com/menu") == f"MAP public-shop.com {FAKE_DNS['public-shop.com']}"
    assert rs._pin_rule("https://93.184.215.14/") is None          # a literal address needs no look-up
    with pytest.raises(rs.ReferenceSiteError):
        rs._pin_rule("https://evil-rebind.com/")
