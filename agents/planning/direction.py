# D:\FYP\FORGE-1\agents\planning\direction.py
"""Design direction (D-239): code deals it, the model repairs fit.

A tuned model asked once returns its favourite look whatever the prompt says (runs 6-8, and the research in
`D:/FYP/reports/Reducing sameness in AI site designs.md`), so the random draws happen here:
1. the business goes into a family by the words in its business type;
2. one of the family's presets is picked, least-used among recent sites of that family first, then by a seed;
3. every choice the preset leaves open is drawn from the family's allowed range with the same seed.
The site-design call gets that start and may change at most 2 choices with a reason (`settle`). A reference
site's measured choices win and are locked; the footer follows the page count."""
import json
import random
import re
import threading
from collections import Counter, deque
from functools import lru_cache
from pathlib import Path

PRESETS_PATH = Path(__file__).resolve().parents[2] / "components" / "design_presets.json"
FIELDS = ("density", "corners", "type_scale", "surfaces", "rhythm", "images", "headings", "hero_variant")
LOCKABLE = ("corners", "images", "rhythm", "type_scale")      # what the reference reader measures
MAX_CHANGES = 2
RECENT = 8                                                       # sites per family remembered for rotation

# shortcut: rotation memory lives in this process and resets on restart; read recent plans from the database
# if sites must stay spread across restarts or several servers.
_recent: dict[str, deque] = {}
_recent_lock = threading.Lock()


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))["families"]


def family_of(business_type: str | None) -> str:
    """The family whose words match the business type most often (whole words); on a tie the later word wins, as
    the last word usually names the business ("wedding photographer"). 'general' when none match."""
    text = f" {re.sub(r'[^a-z0-9é ]+', ' ', (business_type or '').lower())} "
    scores = {name: (sum(f" {w} " in text for w in fam["words"]),
                     max((text.find(f" {w} ") for w in fam["words"]), default=-1))
              for name, fam in load().items()}
    best = max(scores, key=scores.get)
    return best if scores[best][0] else "general"


def start(business_type: str | None, seed: str, reference: dict | None = None) -> dict:
    """The starting direction for one site: {family, preset, direction, allowed, locked}. The pick is recorded
    for rotation, so call it once per site (re-plans reuse the stored start)."""
    family = family_of(business_type)
    fam = load()[family]
    rng = random.Random(seed)
    with _recent_lock:
        used = Counter(_recent.setdefault(family, deque(maxlen=RECENT)))
        fewest = min(used[p["id"]] for p in fam["presets"])
        preset = rng.choice([p for p in fam["presets"] if used[p["id"]] == fewest])
        _recent[family].append(preset["id"])
    direction = {f: preset["fixed"].get(f) or rng.choice(fam["allowed"][f]) for f in FIELDS}
    locked = {f: reference[f] for f in LOCKABLE if (reference or {}).get(f)}
    return {"family": family, "preset": preset["id"], "direction": direction | locked,
            "allowed": fam["allowed"], "locked": sorted(locked)}


def settle(chosen: dict, begin: dict, reasons: dict[str, str], pages: int) -> tuple[dict, list[dict]]:
    """The final direction: the start plus at most 2 of the model's changes, each with a reason, inside the
    family's range and not on a locked choice; everything else goes back to the start. Returns the direction
    (all 9 choices) and the changes kept, for the edit-rate count."""
    out, kept = dict(begin["direction"]), []
    for field in FIELDS:
        value, reason = chosen.get(field), (reasons.get(field) or "").strip()
        if value == out[field] or not reason or field in begin["locked"]:
            continue
        if value in begin["allowed"][field] and len(kept) < MAX_CHANGES:
            kept.append({"field": field, "from": out[field], "to": value, "reason": reason})
            out[field] = value
    out["footer_variant"] = "centred" if pages <= 3 else "columns"
    return out, kept


def forget_recent() -> None:
    """Tests start from an empty rotation."""
    with _recent_lock:
        _recent.clear()
