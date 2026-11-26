# D:\FYP\FORGE-1\agents\clarification\policy.py
"""
What FORGE will not build, and private numbers it will not keep (D-255, examiner testing W1-W5).

1. `code_guard(text)`: a category when the text plainly asks for a harmful site, else None. Deliberately narrow:
   every pattern needs the harmful intent next to its target ("UNLICENSED firearms", "COLLECT people's passwords",
   "hate AGAINST a religious group"), so a licensed gun shop, a pharmacy, a lingerie shop, adult education or a
   religious centre never matches. The intake model is the second layer (message_kind "prohibited").
2. `mask_private(text)`: card numbers (13-19 digits that pass the Luhn check) and CNICs become placeholders before
   the text reaches the model or FORGE's database. Phones and emails stay: owners give their own for the site.
"""
import re

CATEGORIES = {
    "credential_theft": "sites that collect other people's passwords or copy a real bank's or company's login page",
    "illegal_trade": "sites that sell illegal goods, such as unlicensed weapons, illegal drugs or forged documents",
    "sexual_content": "sites with sexual or pornographic content",
    "hate_or_violence": "sites that spread hate or violence against people or a group",
    "scam": "sites made to trick people out of their money",
}

_GROUP = (r"(muslims?|christians?|jews?|jewish|hindus?|sikhs?|ahmadis?|shias?|sunnis?|parsis?|religio\w*|"
          r"ethnic\w*|races?|minorit\w*|women|gays?|lgbt\w*|immigrants?|refugees?|people|community|group)")
_BRAND = (r"(bank|hbl|ubl|mcb|meezan|allied bank|easypaisa|jazzcash|paypal|facebook|instagram|gmail|google|"
          r"microsoft|apple|amazon|netflix|daraz)")

_PATTERNS: list[tuple[str, re.Pattern]] = [(cat, re.compile(p, re.I)) for cat, p in [
    ("credential_theft", r"\b(collect|steal|harvest|capture|grab|record|phish)\w*\b[^.]{0,40}?\b(passwords?|"
                         r"log-?in details|credentials|otps?|pin codes?|card details)\b"),
    # a phishing SITE, not the word: "teach people to spot scams and phishing" is legal (Round 2, V09)
    ("credential_theft", r"\bphishing\s+(sites?|pages?|websites?|links?|kits?|emails?)\b"
                         r"(?![^.]{0,30}\b(awareness|training|protect\w*|prevent\w*|course|test\w*|spot\w*))"),
    ("credential_theft", r"\b(copy|clone|replica|imitat\w*|exactly like|identical to|fake)\b[^.]{0,40}?\b" + _BRAND
                         + r"\b[^.]{0,30}?\b(log-?in|sign[- ]?in)\b"),
    ("illegal_trade", r"\b(unlicensed|illegal|unregistered|black[- ]market|smuggled|stolen)\s+(guns?|firearms?|"
                      r"weapons?|pistols?|rifles?|ammunition|ammo|drugs?|medicines?|cars?|phones?|goods)\b"),
    ("illegal_trade", r"\b(sell|selling|buy|deliver|supply|order)\w*\b[^.]{0,30}?\b(cocaine|heroin|meth|"
                      r"methamphetamine|ecstasy|mdma|lsd)\b"),
    ("illegal_trade", r"\b(fake|forged|counterfeit)\s+(passports?|degrees?|diplomas?|id cards?|ids|cnics?|"
                      r"licen[cs]es?|documents?|currency|money|notes)\b"),
    ("sexual_content", r"\b(porn\w*|xxx|sex videos?|explicit (videos?|photos?|images?|content)|nude (photos?|"
                       r"videos?|images?)|escort services?|call girls?)\b"),
    ("hate_or_violence", r"\b(hate|hatred|hostility|violence)\s+(against|towards?)\s+(\w+\s+){0,3}" + _GROUP + r"\b"),
    ("hate_or_violence", r"\b(kill|attack|bomb|exterminate)\w*\s+(all\s+)?" + _GROUP + r"\b"),
    ("scam", r"\b(ponzi|pyramid scheme|money doubling|double your money)\b"),
    ("scam", r"\bscam\w*\s+(people|visitors|customers|users)\b"),
]]


def code_guard(text: str) -> str | None:
    """The category of a plainly harmful request, else None (the model is the second, wider layer)."""
    for category, pattern in _PATTERNS:
        if pattern.search(text or ""):
            return category
    return None


def refusal(category: str) -> str:
    what = CATEGORIES.get(category, "this kind of site")
    return (f"FORGE can't build {what}. If you have a different website in mind, tell me what it's for and "
            "I'll get started.")


_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_CNIC = re.compile(r"(?<!\d)\d{5}-?\d{7}-?\d(?!\d)")


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def mask_private(text: str) -> str:
    """Card numbers and CNICs out; everything else as written."""
    if not text:
        return text

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return "[card number removed]" if 13 <= len(digits) <= 19 and _luhn(digits) else m.group(0)
    text = _CNIC.sub("[CNIC removed]", text)
    return _CARD.sub(card, text)
