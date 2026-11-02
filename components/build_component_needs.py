# D:\FYP\FORGE-1\components\build_component_needs.py
"""
Builds component_needs.json: for every component, what it needs to render fully (Planning Agent, plan v2 §3).
Run after changing a component's Props:  .venv\\Scripts\\python.exe components\\build_component_needs.py

Each input of a component's `XxxProps` interface gets one kind:
  copy     text shown on the site, written by the AI (with length limits)
  fact     one business fact the owner gives (phone, address...), linked to a content key when one exists
  list     a list of items the owner gives (services, team, FAQs); its item fields are described too
  image    a picture the owner uploads (logo, photos)
  setting  links, layout and switches chosen by the plan
  live     data the site's backend supplies while running (free time slots)
  code     callbacks, className and automatic lines wired by the frontend generator; not a need
Name rules decide most kinds; OVERRIDES holds the decisions checked by hand, so re-running keeps them.
tests/test_component_needs.py fails when a Props input is missing here.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "component_needs.json"

# Catalogue ids whose file name is not the id in PascalCase
FILE_FOR_ID = {"hero-banner": "Hero", "about-us": "About", "whatsapp-button": "WhatsAppButton"}
# Site-level parts with no catalogue entry (every generated site may use them)
EXTRA_FILES = {"SeoHead": "seo-head", "NotFoundPage": "not-found-page", "LoadingAndErrorStates": "loading-and-error-states"}

CONTENT_KEYS = {"business_name", "phone", "whatsapp", "email", "address", "map_embed_url", "hours", "social_handles",
                "logo", "photos", "items", "prices", "about_text", "video_url"}
FACT_KEYS = {  # prop name (lower case) -> catalogue content key
    "brandname": "business_name", "businessname": "business_name", "companyname": "business_name",
    "phone": "phone", "phonenumber": "phone", "email": "email", "address": "address",
    "whatsapp": "whatsapp", "whatsappnumber": "whatsapp", "phonenumberwhatsapp": "whatsapp",
    "mapembedurl": "map_embed_url", "embedurl": "map_embed_url", "videourl": "video_url",
    "sociallinks": "social_handles", "socialhandles": "social_handles", "socials": "social_handles",
    "hours": "hours", "openinghours": "hours", "schedule": "hours",
}
COPY_LIMITS = [  # (name pattern, max characters) - first match wins
    (r"^(headline|heading)$", 70), (r"^subheadline$", 180), (r"(^|_)title$|Title$", 70),
    (r"subtitle$|Subtitle$", 180), (r"badge", 32), (r"(cta|button|submit).*text$|ButtonText$|CtaText$", 28),
    (r"label$|Label$", 32), (r"placeholder", 60), (r"message$|Message$", 160), (r"footnote|disclaimer", 200),
    (r"description$|Description$|intro|text$|Text$|body|content|story", 400), (r".*", 120),
]
IMAGE_NAME = re.compile(r"(image|img|logo|photo|avatar|src|thumbnail|background|poster|cover)(url|src)?$", re.I)
ALT_NAME = re.compile(r"alt$", re.I)
LINK_NAME = re.compile(r"(href|link|path|route)$", re.I)
SETTING_TYPES = re.compile(r"^(boolean|number|\"[^\"]+\"(\s*\|\s*\"[^\"]+\")*)$")

# Hand-checked decisions: (component id, input) -> fields to set. Reviewed 2026-11-04.
PLAN = {"kind": "setting", "source": "plan"}          # filled from the plan (navigation, page links)
LIVE = {"kind": "live", "required": True}             # the site's backend supplies it (catalogue dataNeeds)
AUTO = {"kind": "code", "required": False}            # made by code from other facts, never asked for
OPTIONAL = {"required": False}
OWNER_TEXT = {"kind": "fact", "required": False}      # text only the owner can know: the AI must not invent it
OVERRIDES: dict[tuple[str, str], dict] = {
    ("booking-form", "timeSlots"): LIVE,
    ("appointment-slot-picker", "availability"): LIVE,
    ("blog-list", "posts"): LIVE,
    ("blog-post", "title"): LIVE, ("blog-post", "subtitle"): LIVE, ("blog-post", "date"): LIVE,
    ("blog-post", "readTime"): LIVE, ("blog-post", "category"): LIVE, ("blog-post", "author"): LIVE,
    ("blog-post", "heroImageUrl"): LIVE, ("blog-post", "heroImageAlt"): LIVE, ("blog-post", "content"): LIVE,
    ("blog-post", "tags"): LIVE, ("blog-post", "shareUrl"): AUTO,
    ("events-list", "events"): LIVE,
    ("search-filter-bar", "totalCount"): AUTO, ("search-filter-bar", "initialCategory"): PLAN,
    ("search-filter-bar", "initialQuery"): PLAN, ("search-filter-bar", "categories"): {**PLAN, "required": False},
    ("navbar", "links"): PLAN, ("footer", "columns"): PLAN, ("page-header", "breadcrumbs"): {**PLAN, "required": False},
    ("footer", "copyright"): AUTO, ("location-map", "directionsUrl"): AUTO, ("blog-post", "backHref"): PLAN,
    ("announcement-bar", "storageKey"): AUTO, ("lead-capture-popup", "storageKey"): AUTO,
    ("cookie-notice", "storageKey"): AUTO, ("legal-page", "lastUpdated"): AUTO, ("seo-head", "canonicalUrl"): AUTO,
    ("seo-head", "children"): AUTO, ("loading-and-error-states", "type"): AUTO,
    ("loading-and-error-states", "count"): AUTO,
    ("legal-page", "sections"): {**AUTO, "note": "standard template filled with the owner's facts, not AI-written"},
    ("about-us", "story"): {"kind": "fact", "content_key": "about_text", "required": True},
    ("about-us", "stats"): OPTIONAL, ("about-us", "features"): OPTIONAL,
    ("lead-capture-popup", "offerBadge"): OWNER_TEXT, ("location-map", "cityStateZip"): {"kind": "fact", "content_key": "address"},
    ("location-map", "additionalInfo"): OWNER_TEXT, ("business-hours", "emergencyNote"): OWNER_TEXT,
    ("business-hours", "timezoneNote"): OWNER_TEXT,
    ("case-study-detail", "clientName"): {"kind": "fact", "required": True}, ("case-study-detail", "year"): OWNER_TEXT,
    ("case-study-detail", "role"): OWNER_TEXT, ("case-study-detail", "summary"): {"kind": "fact", "required": True},
    ("case-study-detail", "challenge"): OWNER_TEXT, ("case-study-detail", "solution"): OWNER_TEXT,
    ("case-study-detail", "result"): OWNER_TEXT, ("case-study-detail", "liveUrl"): OWNER_TEXT,
    ("product-detail", "name"): {"kind": "fact", "content_key": "items", "required": True},
    ("product-detail", "price"): {"kind": "fact", "content_key": "prices", "required": True},
    ("product-detail", "originalPrice"): {"kind": "fact", "content_key": "prices", "required": False},
    ("product-detail", "badge"): OWNER_TEXT, ("product-detail", "description"): OWNER_TEXT,
    ("product-detail", "images"): {"kind": "list", "content_key": "photos", "required": True},
    ("product-detail", "specifications"): {"kind": "list", "required": False},
    ("before-after-slider", "beforeImage"): {"kind": "image", "content_key": "photos", "required": True},
    ("before-after-slider", "afterImage"): {"kind": "image", "content_key": "photos", "required": True},
    ("whatsapp-button", "phoneNumber"): {"kind": "fact", "content_key": "whatsapp", "required": True},
    ("legal-page", "contactEmail"): {"kind": "fact", "content_key": "email", "required": True},
    ("legal-page", "companyName"): {"kind": "fact", "content_key": "business_name", "required": True},
    ("seo-head", "siteName"): {"kind": "fact", "content_key": "business_name", "required": True},
    ("seo-head", "keywords"): {"kind": "copy", "max_length": 40, "required": False, "note": "each keyword"},
    ("contact-form", "phone"): OPTIONAL, ("contact-form", "address"): OPTIONAL,
    ("cta-banner", "highlights"): OPTIONAL, ("blog-list", "categories"): OPTIONAL,
    ("portfolio-grid", "categories"): OPTIONAL, ("menu-catalog-grid", "categories"): OPTIONAL,
    ("image-gallery", "categories"): OPTIONAL, ("services-price-list", "categories"): OPTIONAL,
    ("product-detail", "variants"): OPTIONAL,
    # owner lists: the catalogue content keys their items carry
    ("portfolio-grid", "projects"): {"content_keys": ["photos"]},
    ("menu-catalog-grid", "items"): {"content_keys": ["items", "photos", "prices"]},
    ("image-gallery", "items"): {"content_keys": ["photos"]},
    ("pricing-table", "plans"): {"content_keys": ["prices"]},
    ("testimonials", "items"): {"content_keys": ["photos"]},
    ("team-grid", "members"): {"content_keys": ["photos"]},
    ("logo-cloud", "logos"): {"content_keys": ["logo"]},
    ("order-request-form", "items"): {"content_keys": ["items"]},
    ("product-card-grid", "products"): {"content_keys": ["items", "photos", "prices"]},
    ("gallery-carousel", "images"): {"content_keys": ["photos"]},
    ("services-price-list", "services"): {"content_keys": ["items", "prices"]},
    ("image-text-rows", "rows"): {"content_keys": ["about_text", "photos"]},
    ("social-links-bar", "handles"): {"content_key": "social_handles"},
}
# Catalogue content keys with no input of their own, and where they are used instead.
USED_ELSEWHERE = {
    "hero-banner": {"business_name": "inside the written headline, as {business_name}"},
    "booking-form": {"email": "where booking requests are sent; shown in the success message",
                     "phone": "shown in the success message so customers can call"},
    "order-request-form": {"phone": "shown in the success message so customers can call"},
    "footer": {"email": "a link in the footer columns", "social_handles": "links in the footer columns"},
    "legal-page": {"about_text": "fills the standard legal template"},
}

PROP = re.compile(r"^\s*(?P<name>\w+)(?P<opt>\?)?\s*:\s*(?P<type>.+?)\s*(//\s*(?P<note>.*))?$")
BLOCK = re.compile(r"export\s+(?:interface|type)\s+(?P<name>\w+)(?:\s+extends\s+(?P<base>[\w, ]+?))?\s*(?:=\s*)?\{"
                   r"(?P<body>.*?)\n\}", re.S)


def parse_types(source: str) -> dict[str, list[dict]]:
    """Every exported interface/object type in a file: name -> [{name, optional, type, note}].
    Inherited fields (`interface A extends B`) come first."""
    types, bases = {}, {}
    for block in BLOCK.finditer(source):
        bases[block.group("name")] = [b.strip() for b in (block.group("base") or "").split(",") if b.strip()]
        fields = []
        for line in block.group("body").splitlines():
            if not line.strip() or line.strip().startswith(("//", "[")):
                continue
            m = PROP.match(line)
            if m:
                fields.append({"name": m["name"], "optional": bool(m["opt"]), "type": m["type"].rstrip(";,"),
                               "note": (m["note"] or "").strip()})
        types[block.group("name")] = fields
    for name, parents in bases.items():
        types[name] = [f for p in parents for f in types.get(p, [])] + types[name]
    return types


def copy_limit(name: str) -> int:
    return next(limit for pattern, limit in COPY_LIMITS if re.search(pattern, name))


def guess(name: str, typ: str, types: dict) -> dict:
    """The kind of one Props input, from its name and type."""
    low = name.lower()
    base = typ.replace("[]", "").strip()
    if name == "className" or re.match(r"^on[A-Z]", name):
        need = {"kind": "code"}
        sent = re.search(r"\(\s*\w+\s*:\s*(\w+)\s*\)", typ)
        if sent and sent.group(1) in types:
            need["submits"] = sent.group(1)
        return need
    if low in FACT_KEYS:
        return {"kind": "fact", "content_key": FACT_KEYS[low]}
    if typ.endswith("[]") and base in types:
        return {"kind": "list", "item_type": base}
    if typ.endswith("[]") and base == "string":
        return {"kind": "list", "item_type": "string"}
    if base in types:                                   # one object, e.g. socials
        return {"kind": "fact", "item_type": base}
    if ALT_NAME.search(name):
        return {"kind": "copy", "max_length": 120}
    if IMAGE_NAME.search(name) and typ.startswith("string"):
        return {"kind": "image", "content_key": "logo" if "logo" in low else "photos"}
    if LINK_NAME.search(name):
        return {"kind": "setting", "role": "link"}
    if SETTING_TYPES.match(typ) or typ.startswith('"'):
        return {"kind": "setting"}
    if typ.startswith("string"):
        return {"kind": "copy", "max_length": copy_limit(name)}
    return {"kind": "setting"}


def item_fields(type_name: str, types: dict) -> list[dict]:
    """Fields of one list item: ids are made by code, everything else comes from the owner."""
    fields = []
    for f in types.get(type_name, []):
        name = f["name"]
        if name in ("id", "key", "stepNumber"):
            kind = "code"
        elif re.search(r"^icon", name, re.I):
            kind = "setting"     # the plan picks an icon from the icon set
        elif ALT_NAME.search(name):
            kind = "copy"        # alt text describes the owner's picture; written, never a fact
        else:
            kind = guess(name, f["type"], types)["kind"]
            if kind == "copy":
                kind = "fact"    # inside an owner's list, text is the owner's (service names, quotes)
        fields.append({"name": f["name"], "kind": kind, "type": f["type"], "required": not f["optional"],
                       **({"note": f["note"]} if f["note"] else {})})
    return fields


def build() -> dict:
    catalogue = json.loads((HERE / "components_catalog.json").read_text(encoding="utf-8"))
    entries = [(e["component_id"], FILE_FOR_ID.get(e["component_id"], "".join(w.capitalize() for w in e["component_id"].split("-"))), True)
               for e in catalogue]
    entries += [(cid, file, False) for file, cid in EXTRA_FILES.items()]
    result = {}
    for cid, file, in_catalogue in entries:
        source = (HERE / f"{file}.tsx").read_text(encoding="utf-8")
        types = parse_types(source)
        props_name = f"{file}Props" if f"{file}Props" in types else next(n for n in types if n.endswith("Props"))
        needs = []
        for prop in types[props_name]:
            need = {"name": prop["name"], "type": prop["type"], **guess(prop["name"], prop["type"], types)}
            need["required"] = need["kind"] in ("list", "fact") or bool(re.search(r"^(headline|title|heading)$", prop["name"]))
            if prop["note"]:
                need["note"] = prop["note"]
            need.update(OVERRIDES.get((cid, prop["name"]), {}))
            if need["kind"] == "list" and need.get("item_type") in types:
                need["item_fields"] = item_fields(need["item_type"], types)
            if need.get("submits"):
                need["submit_fields"] = item_fields(need["submits"], types)
            needs.append(need)
        result[cid] = {"file": f"{file}.tsx", "props": props_name, "in_catalogue": in_catalogue, "needs": needs,
                       **({"content_used_elsewhere": USED_ELSEWHERE[cid]} if cid in USED_ELSEWHERE else {})}
    return result


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(data)} components, {sum(len(c['needs']) for c in data.values())} inputs")
