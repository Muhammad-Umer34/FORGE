# D:\FYP\FORGE-1\agents\frontend_generator\photos.py
"""Stock photos for generated sites (D-240): checked Unsplash photos per business family (the D-239 families) plus a
"people" list for team, testimonial and author pictures. Dealt in a seeded order, so one site never repeats a photo
and the same site always gets the same photos. Unsplash's licence allows free use and hotlinking. A family with no
photos gets a soft placeholder tinted with the site's main colour, so a site still works offline."""
import json
import random
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

PHOTOS_PATH = Path(__file__).resolve().parents[2] / "components" / "stock_photos.json"
URL = "https://images.unsplash.com/photo-{id}?auto=format&fit=crop&w={w}&q=80"


@lru_cache(maxsize=1)
def load() -> dict[str, list[str]]:
    if not PHOTOS_PATH.exists():
        return {}
    return json.loads(PHOTOS_PATH.read_text(encoding="utf-8"))["photos"]


def placeholder(colour: str = "#9a3412", label: str = "") -> str:
    """A soft gradient picture as a data URL, coloured from the theme."""
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 1000'><defs><linearGradient id='g' x1='0' "
           f"y1='0' x2='1' y2='1'><stop offset='0' stop-color='{colour}' stop-opacity='.85'/><stop offset='1' "
           f"stop-color='{colour}' stop-opacity='.35'/></linearGradient></defs><rect width='1600' height='1000' "
           f"fill='url(#g)'/></svg>")
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


class Dealer:
    """Deals photos for one site: a different one each call until the list runs out, then from the start again."""

    def __init__(self, family: str, seed: str, colour: str = "#9a3412"):
        rng = random.Random(f"photos:{seed}")
        self._places = list(load().get(family) or load().get("general") or [])
        self._people = list(load().get("people") or [])
        rng.shuffle(self._places)
        rng.shuffle(self._people)
        self._next = {"place": 0, "person": 0}
        self._colour = colour

    def _deal(self, pool: list[str], which: str, width: int) -> str:
        if not pool:
            return placeholder(self._colour)
        photo = pool[self._next[which] % len(pool)]
        self._next[which] += 1
        return URL.format(id=photo, w=width)

    def photo(self, width: int = 1600) -> str:
        return self._deal(self._places, "place", width)

    def person(self) -> str:
        return self._deal(self._people, "person", 400)
