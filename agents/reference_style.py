# D:\FYP\FORGE-1\agents\reference_style.py
"""
"Make it look like this website" (theme Phase 2, decisions D-165 - D-168).

Opens ONE page of the website in a headless browser (Playwright) and reads the browser's computed
styles: page background, text colour, main brand colour (buttons and links), heading and body fonts,
button corner radius, and whether the site is dark. Nothing else is taken - no layout, text, images,
logos or brand names - because FORGE builds with its own components and only the style can transfer.

Safety (server-side request forgery): only http/https on ports 80/443, the address must resolve to
public internet addresses only, every request the page makes is checked again (images, fonts and
media are not loaded at all), the final address after redirects is checked, and the browser runs
in a separate process with a time limit.

Run directly for one site:  python -m agents.reference_style https://example.com
"""
import ipaddress
import json
import os
import re
import socket
import statistics
import subprocess
import sys
import threading
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

PAGE_TIMEOUT_MS = 15_000          # loading the page
SETTLE_MS = 3_000                 # extra wait for scripts that add styles
PROCESS_TIMEOUT_S = 30            # hard limit for the whole browser process
VIEWPORT = {"width": 1280, "height": 800}
_BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home.arpa")
_URL_IN_TEXT = re.compile(r"(?:https?://|www\.)[^\s<>\"'()]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|pk|io|co|uk|dev|app|shop|store|site)\b(?:/[^\s<>\"'()]*)?", re.IGNORECASE)
ROOT = Path(__file__).resolve().parents[1]
_BROWSER_DEFAULT_LINKS = {"#0000ee", "#551a8b", "#0000ff"}   # unstyled links say nothing about the brand


class ReferenceSiteError(ValueError):
    """A problem reading the website, worded for the user."""


# ---------------------------------------------------------------- the address
def find_url(text: str) -> str | None:
    """The first website address written in the user's text ('make it look like www.example.com')."""
    match = _URL_IN_TEXT.search(text or "")
    return match.group(0).rstrip(".,;:!?") if match else None


def normalise_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ReferenceSiteError("Please paste a website address.")
    if "://" not in raw:
        raw = "https://" + raw
    return raw


def _is_public(ip: str) -> bool:
    address = ipaddress.ip_address(ip)
    return address.is_global and not address.is_multicast


@lru_cache(maxsize=256)
def _host_is_public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    addresses = {info[4][0].split("%")[0] for info in infos}
    return bool(addresses) and all(_is_public(a) for a in addresses)


def check_url(url: str) -> str:
    """Raise ReferenceSiteError unless the address is a normal public website. Returns the URL."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ReferenceSiteError("Only normal website addresses (http or https) can be used.")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise ReferenceSiteError("That doesn't look like a website address.")
    try:
        port = parts.port
    except ValueError:
        raise ReferenceSiteError("That doesn't look like a website address.")
    if port not in (None, 80, 443):
        raise ReferenceSiteError("Only normal website addresses can be used (no special ports).")
    if parts.username or parts.password:
        raise ReferenceSiteError("Website addresses with a user name or password can't be used.")
    if host == "localhost" or host.endswith(_BLOCKED_SUFFIXES):
        raise ReferenceSiteError("That address is not a public website.")
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        literal = None
    if literal is not None and not _is_public(str(literal)):
        raise ReferenceSiteError("That address is not a public website.")
    if literal is None and not _host_is_public(host):
        raise ReferenceSiteError("We couldn't find that website, or it is not a public site.")
    return url


def _request_allowed(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme in ("data", "blob", "about"):
        return True
    try:
        check_url(url)
        return True
    except ReferenceSiteError:
        return False


# ---------------------------------------------------------------- reading the page (runs in the child process)
_EXTRACT_JS = """() => {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const rgba = (c) => {                              // any CSS colour (rgb, oklch, named...) -> [r,g,b,a]
    if (!c) return null;
    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = 'rgba(0,0,0,0)'; ctx.fillStyle = c; ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3]];
  };
  const cs = (el) => getComputedStyle(el);
  const box = (el) => el.getBoundingClientRect();
  const visible = (el) => { const r = box(el); return r.width > 4 && r.height > 4 && r.top < 2400; };
  const solidBg = (el) => { for (let e = el; e; e = e.parentElement) { const c = rgba(cs(e).backgroundColor); if (c && c[3] > 200) return c; } return [255, 255, 255, 255]; };
  const heading = document.querySelector('h1') || document.querySelector('h2') || document.body;
  const sel = 'button, [role="button"], input[type="submit"], a[class*="btn" i], a[class*="button" i], a[class*="cta" i]';
  const buttons = [...document.querySelectorAll(sel)].filter(visible).slice(0, 40).map((b) => {
    const r = box(b); return { bg: rgba(cs(b).backgroundColor), radius: parseFloat(cs(b).borderTopLeftRadius) || 0, height: r.height, area: Math.round(r.width * r.height) };
  });
  const links = [...document.querySelectorAll('a')].filter(visible).slice(0, 80).map((a) => rgba(cs(a).color));
  const header = document.querySelector('header, nav, [role="banner"]');
  // Large coloured blocks near the top (hero sections, banners): total area per colour, biggest first.
  const blockArea = {};
  [...document.querySelectorAll('body *')].slice(0, 2500).forEach((el) => {
    const r = box(el);
    if (r.width < 24 || r.height < 16 || r.top > 1600 || r.bottom < 0) return;
    const c = rgba(cs(el).backgroundColor);
    if (!c || c[3] < 200) return;
    const key = c.slice(0, 3).join(',');
    blockArea[key] = (blockArea[key] || 0) + Math.min(r.width * r.height, 1280 * 800);
  });
  const blocks = Object.entries(blockArea).sort((a, b) => b[1] - a[1]).slice(0, 15)
    .map(([k, area]) => ({ bg: [...k.split(',').map(Number), 255], area: Math.round(area) }));
  return {
    blocks,
    background: solidBg(document.body), text: rgba(cs(document.body).color),
    heading_font: cs(heading).fontFamily, heading_weight: cs(heading).fontWeight, body_font: cs(document.body).fontFamily,
    buttons, links, header_bg: header ? rgba(cs(header).backgroundColor) : null,
  };
}"""


def read_in_process(url: str, html: str | None = None) -> dict:
    """
    Open the page and return the raw computed styles. `html` loads given HTML instead of a URL
    (used by the offline tests: nothing is fetched from the network).
    """
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(viewport=VIEWPORT, accept_downloads=False, service_workers="block")
            page = context.new_page()

            def guard(route):
                request = route.request
                if request.resource_type in ("image", "media", "font") or not _request_allowed(request.url):
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", guard)
            if html is not None:
                page.set_content(html, wait_until="domcontentloaded")
            else:
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                except PlaywrightTimeout:
                    raise ReferenceSiteError("The website took too long to open.")
                except PlaywrightError:
                    raise ReferenceSiteError("We couldn't open that website.")
                if response is None or response.status >= 400:
                    raise ReferenceSiteError("The website didn't open correctly (it may need a login or block visitors like us).")
                check_url(page.url)                     # the address after any redirects must still be public
                try:
                    page.wait_for_load_state("networkidle", timeout=SETTLE_MS)
                except PlaywrightTimeout:
                    pass
            return page.evaluate(_EXTRACT_JS)
        finally:
            browser.close()


# ---------------------------------------------------------------- turning raw styles into a theme source
def _hex(rgba: list | None) -> str | None:
    if not rgba or rgba[3] < 200:
        return None
    return "#{:02x}{:02x}{:02x}".format(*rgba[:3])


def _radius(px: float) -> str:
    if px <= 2:
        return "0.25rem"
    if px <= 5:
        return "0.375rem"
    if px <= 9:
        return "0.5rem"
    if px <= 14:
        return "0.75rem"
    return "1rem"


def summarise(raw: dict, url: str) -> dict:
    """Pure function: raw computed styles -> the small style summary FORGE keeps (D-166)."""
    from agents import theming

    background = _hex(raw.get("background")) or "#ffffff"
    text = _hex(raw.get("text")) or "#111111"

    def vivid(hex_colour: str | None) -> bool:
        return bool(hex_colour) and theming.chroma_of(hex_colour) >= 16 and theming.contrast_ratio(hex_colour, background) >= 1.3

    weights: dict[str, float] = {}
    for block in raw.get("blocks") or []:            # big coloured areas: hero sections, banners, badges
        colour = _hex(block.get("bg"))
        if vivid(colour):
            weights[colour] = weights.get(colour, 0) + min(6.0, (block.get("area") or 0) / 40000)
    for b in raw.get("buttons") or []:
        colour = _hex(b.get("bg"))
        if vivid(colour):
            weights[colour] = weights.get(colour, 0) + 3 + (b.get("area") or 0) / 5000
    for link in raw.get("links") or []:
        colour = _hex(link)
        if vivid(colour) and colour not in _BROWSER_DEFAULT_LINKS:
            weights[colour] = weights.get(colour, 0) + 1
    header = _hex(raw.get("header_bg"))
    if vivid(header):
        weights[header] = weights.get(header, 0) + 2
    primary = max(weights, key=weights.get) if weights else None

    radii = []
    for b in raw.get("buttons") or []:
        if _hex(b.get("bg")):
            r = b.get("radius") or 0
            radii.append(32 if b.get("height") and r >= b["height"] / 2 - 1 else r)   # pill shape -> most rounded
    radius = _radius(statistics.median(radii)) if radii else None

    pair_id, exact = theming.closest_font_pair(raw.get("heading_font") or "", raw.get("body_font") or "")
    heading_name = theming.first_font(raw.get("heading_font") or "")
    is_dark = theming.luminance(background) < 0.2
    if theming.font_class(raw.get("heading_font") or "") == "serif":
        personality = "elegant"
    elif radius == "1rem":
        personality = "playful"
    elif primary and theming.chroma_of(primary) >= 60:
        personality = "bold"
    else:
        personality = "professional"

    notes = []
    if not primary:
        notes.append("No clear brand colour was found, so a colour that suits your business is used.")
    if heading_name and not exact:
        pair = next(p for p in theming.load_presets()["font_pairs"] if p["id"] == pair_id)
        notes.append(f"{heading_name} isn't a free font we can use; the closest free match is {pair['heading']}.")
    return {
        "url": url,
        "host": (urlsplit(url).hostname or "").removeprefix("www."),
        "background": background,
        "text": text,
        "primary": primary,
        "is_dark": is_dark,
        "radius": radius,
        "font_pair_id": pair_id,
        "fonts_exact": exact,
        "heading_font_source": heading_name,
        "personality": personality,
        "notes": notes,
    }


def _run_browser(url: str) -> subprocess.CompletedProcess:
    """One page read in a separate browser process, killed after PROCESS_TIMEOUT_S."""
    try:
        return subprocess.run(
            [sys.executable, "-m", "agents.reference_style", url],
            cwd=ROOT, capture_output=True, text=True, timeout=PROCESS_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        raise ReferenceSiteError("The website took too long to open.")


# At most this many reading browsers at once (each needs about 200-300 MB of memory); a request
# waits up to READER_WAIT_S for a free one, then gets a "busy" notice (D-193).
MAX_BROWSERS = int(os.getenv("READER_MAX_BROWSERS", "2"))
READER_WAIT_S = float(os.getenv("READER_WAIT_S", "20"))
_browsers = threading.BoundedSemaphore(MAX_BROWSERS)


def read_reference(url: str) -> dict:
    """
    Check the address, read ONE page in a separate browser process, and return the style summary.
    Raises ReferenceSiteError with a plain message when the site can't be used.
    """
    url = check_url(normalise_url(url))
    if not _browsers.acquire(timeout=READER_WAIT_S):
        raise ReferenceSiteError("FORGE is busy reading other websites. Please try again in a minute.")
    try:
        done = _run_browser(url)
    finally:
        _browsers.release()
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    try:
        result = json.loads(lines[-1]) if lines else {}
    except json.JSONDecodeError:
        result = {}
    if "error" in result:
        raise ReferenceSiteError(result["error"])
    if "raw" not in result:
        raise ReferenceSiteError("We couldn't read that website.")
    return summarise(result["raw"], url)


if __name__ == "__main__":   # child process: print one JSON line, never a traceback
    try:
        target = check_url(normalise_url(sys.argv[1]))
        print(json.dumps({"raw": read_in_process(target)}))
    except ReferenceSiteError as error:
        print(json.dumps({"error": str(error)}))
    except Exception:  # browser crash, missing browser, anything else
        print(json.dumps({"error": "We couldn't read that website."}))
