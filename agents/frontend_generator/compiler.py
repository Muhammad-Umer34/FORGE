# D:\FYP\FORGE-1\agents\frontend_generator\compiler.py
"""
The frontend agent, version 1 (D-240): an approved Build Plan in, the site's files out. No model call: every file is
made by code, so the same plan and seed always give the same files (Phase 3 plan, item 3.1) and every prop can be
type-checked against its component.

Where each component input comes from (kinds from components/component_needs.json):
- copy: the plan's texts (slot `section.prop`), with {placeholders} filled from the sample content;
- fact, list, image: the sample content (key from content_schema.section_keys), shaped to the input's type;
- setting: the section's settings; links, menu and footer columns made from the pages;
- live: sample data until the backend agent exists;
- code: left out (handlers, className), except the copyright line.
Backend and database agents come later: forms show their success message but store nothing yet.
"""
import json
import re
from typing import Any

from agents.frontend_generator.photos import Dealer
from agents.planning import direction as design
from agents.planning import fixed
from agents.planning.content_schema import load_needs, needs_of, section_keys
from agents.state import BuildPlan, PlannedComponent

DEFAULT_FONT = "Inter"
DEFAULT_RADIUS = "0.625rem"
IMAGE_FIELDS = {"src", "url", "imageUrl", "image", "heroImageUrl", "backgroundImageUrl", "ogImageUrl", "photo"}
PERSON_FIELDS = {"avatarUrl"}
LEFT_OUT = {"logoUrl", "className", "canonicalUrl", "children", "shareUrl"}
FALLBACK_PART = "cta-banner"          # what a custom part shows until the custom-part writer exists (D-240)
LIST_LENGTH = 3
_PRICE = re.compile(r"price|cost|fee|amount|total")
TIME_SLOTS = ["10:00", "11:30", "14:00", "16:30"]
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SOCIAL = {"instagram": "https://instagram.com/", "facebook": "https://facebook.com/"}
ICONS = ["Sparkles", "Star", "Heart", "Clock", "ShieldCheck", "Award"]
# List items read as obvious placeholders, never real-looking facts (D-225): a noun from the list's name and a plain
# sample per field name. The owner's details replace them later.
NOUNS = {"services": "Service", "items": "Item", "members": "Team member", "plans": "Plan", "features": "Feature",
         "products": "Product", "projects": "Project", "images": "Photo", "steps": "Step", "stats": "Highlight",
         "rows": "Highlight", "logos": "Partner", "skills": "Skill", "experience": "Role", "education": "Course",
         "metrics": "Result", "gallery": "Photo"}
LONG = "A short description goes here. Replace it with your own words."
FIELD_SAMPLES = {
    "description": LONG, "bio": LONG, "detail": LONG, "caption": LONG, "answer": LONG, "excerpt": LONG,
    "price": "Rs. 0,000", "yearlyPrice": "Rs. 00,000", "duration": "00 min", "category": "Category",
    "badge": "New", "tag": "Tag", "value": "00+", "trend": "+0%", "role": "Role title", "company": "Company name",
    "client": "Client name", "author": "Customer name", "quote": "A short quote from a happy customer goes here.",
    "date": "January 1, 2026", "period": "2020 - 2026", "degree": "Degree name", "institution": "Institution name",
    "year": "2026", "level": "Advanced", "credentials": "Qualification", "email": "hello@example.com",
    "buttonLabel": "Learn more", "ctaText": "Learn more",
}


def _name(component_id: str) -> str:
    """The component's export name: its file name without .tsx."""
    return load_needs()[component_id]["file"].removesuffix(".tsx")


def _suffix(section_id: str) -> str:
    return section_id.split(".", 1)[1] if "." in section_id else section_id


def _js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _setting(need: dict, value: Any) -> Any:
    """A setting from the plan, shaped to the input's type: the model writes "3" where the type is 2 | 3 | 4, and
    "true" where it is boolean. A value the type does not allow is dropped, so the component's default applies."""
    if value is None:
        return None
    ntype = need.get("type", "string")
    literals = re.findall(r'"([^"]*)"|(?<![\w.])(-?\d+(?:\.\d+)?)(?![\w.])', ntype) if "|" in ntype else []
    if literals:
        allowed = [s if s or not n else (float(n) if "." in n else int(n)) for s, n in literals]
        for option in allowed:
            if str(option) == str(value).strip():
                return option
        return None
    if ntype == "boolean":
        return value if isinstance(value, bool) else str(value).strip().lower() == "true"
    if ntype == "number":
        try:
            return float(value) if "." in str(value) else int(value)
        except (TypeError, ValueError):
            return None
    return value


class Site:
    """Everything one compile needs, worked out once from the plan."""

    def __init__(self, plan: BuildPlan, business_type: str | None, seed: str, written: dict | None = None):
        self.plan = plan
        self.written = written or {}              # section id -> {"module", "export_name"} of a model-written part
        self.modules: dict[str, str] = {}         # export name -> import path, for parts outside components/
        from agents.backend_generator.agent import form_specs
        self.forms = form_specs(plan)             # section id -> its DataForm spec (D-248)
        self.sample = plan.sample_content or {}
        self.business = self.sample.get("business_name") or f"Your {(business_type or 'business').title()}"
        self.texts = {(t.section_id, t.prop): t.text for t in plan.texts if t.text}
        self.specs = {s.spec_id: s for s in plan.custom_specs}
        self.pages = {p.page_id: p for p in plan.pages}
        self.sections = {c.section_id: c for c in plan.components}
        tokens = (plan.theme or {}).get("tokens") or {}
        self.light, self.dark = tokens.get("light") or {}, tokens.get("dark") or {}
        self.photos = Dealer(design.family_of(business_type), seed, self.light.get("primary", "#9a3412"))
        self.menu = sorted((p for p in plan.pages if p.in_menu and "[" not in p.route), key=lambda p: p.menu_order)
        self.target = next((p.route for key in ("booking", "contact") for p in plan.pages
                            if key in p.page_id and "[" not in p.route), None)

    # ------------------------------------------------------------ texts and placeholders
    def fill(self, text: str) -> str:
        """{business_name} and other content keys replaced by their sample values; an unknown one is dropped."""
        def one(m: re.Match) -> str:
            value = self.sample.get(m.group(1))
            return value if isinstance(value, str) else (self.business if m.group(1) == "business_name" else "")
        return re.sub(r"\s{2,}", " ", re.sub(r"\{([a-z0-9_]+)\}", one, text)).strip()

    def text(self, section_id: str, prop: str) -> str | None:
        value = self.texts.get((section_id, prop))
        return self.fill(value) if value else None

    # ------------------------------------------------------------ links
    def link(self, section: PlannedComponent, name: str) -> str:
        """A link nobody set: home links go home; the main call to action goes to booking or contact."""
        if "home" in name.lower() or "back" in name.lower():
            return "/"
        page = self.pages.get(section.page)
        on_page = [s for s in (page.section_ids if page else []) if any(k in s for k in ("contact", "booking"))]
        if "secondary" in name.lower():
            other = next((p.route for p in self.menu if p.route not in ("/", self.target)), None)
            if other:
                return other
        if self.target and (not page or page.route != self.target):
            return self.target
        return f"#section-{_suffix(on_page[0])}" if on_page else "/"

    def nav_links(self) -> list[dict]:
        return [{"label": p.title, "href": p.route} for p in self.menu]

    def footer_columns(self) -> list[dict]:
        pages = [self.pages[p] for p in self.plan.footer_links if p in self.pages] or self.menu
        return [{"title": "Pages", "links": [{"label": p.title, "href": p.route} for p in pages]}]

    # ------------------------------------------------------------ values shaped to their type
    def picture(self, field: str) -> str:
        return self.photos.person() if field in PERSON_FIELDS else self.photos.photo()

    def item(self, fields: list[dict], given: dict, key: str, n: int) -> dict:
        out: dict[str, Any] = {}
        for i, f in enumerate(fields):
            name, ftype, value = f["name"], f.get("type", "string"), given.get(f["name"])
            if "=>" in ftype:
                continue                                 # handlers inside items are left out, like top-level ones
            if ftype.startswith("{"):
                # The Needs List flattens a nested object: the fields after it are its own (actionLink: label, href).
                nested = given.get(name)
                out[name] = self.item(fields[i + 1:], nested if isinstance(nested, dict) else {}, key, n)
                break
            if f.get("role") == "link" or name in ("href", "ctaHref", "link"):
                out[name] = self.target or "/"
            elif name == "id":
                out[name] = f"{key.replace('_', '-')}-{n}"
            elif name in IMAGE_FIELDS or name in PERSON_FIELDS or f.get("kind") == "image":
                out[name] = self.picture(name)
            elif ftype == "boolean":
                out[name] = n == 1 if name.startswith("is") else bool(value)
            elif ftype == "money" or _PRICE.search(name.lower()):
                # round, rising amounts: a calculator or price list shows a working total, and under the sample
                # banner nobody takes Rs. 1,000 for a real price (D-225, D-241)
                out[name] = n * 1000 if ftype == "number" else f"Rs. {n * 1000:,}"
            elif ftype == "number":
                out[name] = value if isinstance(value, (int, float)) and not isinstance(value, bool) else n
            elif ftype == "number | string":
                out[name] = n
            elif ftype == "string[]":
                out[name] = [f"Sample {name} one", f"Sample {name} two"]
            elif isinstance(value, str) and value and not value.startswith("Sample "):
                out[name] = value
            else:
                out[name] = self.sample_text(name, key, n)
        return out

    def sample_text(self, field: str, key: str, n: int) -> str:
        last = key.split("_")[-1]
        noun = NOUNS.get(last) or (last[:-3] + "y" if last.endswith("ies") else last.rstrip("s")).capitalize() or "Item"
        if field == "iconName":
            return ICONS[(n - 1) % len(ICONS)]
        if field in ("name", "title", "label", "question") or field.endswith(("_name", "_title", "_label", "Name")):
            return f"{noun} {n}" + ("?" if field == "question" else "")
        if field in ("alt", "imageAlt"):
            return f"{noun} {n} photo"
        return FIELD_SAMPLES.get(field, f"Sample {field.replace('_', ' ').lower()} {n}")

    def items(self, need: dict, key: str) -> list[dict]:
        given = self.sample.get(key)
        rows = given if isinstance(given, list) and given else [{}] * LIST_LENGTH
        return [self.item(need.get("item_fields") or [], r if isinstance(r, dict) else {}, key, n)
                for n, r in enumerate(rows[:6], 1)]

    def structured(self, ntype: str, name: str, key: str) -> Any:
        """Inputs whose type has no item fields in the Needs List: shapes read from the component files."""
        if ntype == "SliderImageData":
            return {"src": self.photos.photo(), "alt": f"{name.replace('Image', '')} photo",
                    "label": "Before" if "before" in name.lower() else "After"}
        if ntype == "BlogPostAuthor":
            return {"name": "Sample Author", "title": "Writer", "avatarUrl": self.photos.person()}
        if ntype in ("SocialLinks", "SocialHandlesMap"):
            return dict(SOCIAL)
        if ntype == "DaySchedule[]":
            return [{"day": d, "dayIndex": i, "isClosed": i == 0, **({} if i == 0 else
                     {"openTime": "09:00", "closeTime": "18:00", "displayHours": "9:00 AM - 6:00 PM"})}
                    for i, d in enumerate(DAYS)]
        if ntype == "BlogPostItem[]":
            return [{"id": f"post-{n}", "title": f"Sample post {n}", "date": f"2026-12-0{n}",
                     "excerpt": "A short sample summary of this post.", "category": "News",
                     "imageUrl": self.photos.photo(1200), "href": f"/blog/sample-post-{n}", "readTime": "3 min read",
                     "author": {"name": "Sample Author", "avatarUrl": self.photos.person()}} for n in range(1, 4)]
        if ntype == "EventItem[]":
            return [{"id": f"event-{n}", "title": f"Sample event {n}", "date": f"December {n * 7}, 2026",
                     "month": "DEC", "day": str(n * 7), "time": "6:00 PM - 8:00 PM", "location": "Sample venue",
                     "description": "A short sample description of this event.", "category": "Event",
                     "isoDate": f"2026-12-{n * 7:02d}"} for n in range(1, 4)]
        if ntype == "Record<string, string[]>":
            return {f"2026-12-0{n}": list(TIME_SLOTS) for n in range(1, 6)}
        if ntype == "{ src: string; alt?: string }[]":
            return [{"src": self.photos.photo(), "alt": f"Photo {n}"} for n in range(1, 5)]
        if ntype == "{ label: string; value: string }[]":
            return [{"label": f"Sample detail {n}", "value": f"Sample value {n}"} for n in range(1, 4)]
        return None

    def content(self, need: dict, key: str) -> Any:
        ntype, name = need.get("type", "string"), need["name"]
        if need["kind"] == "image" or name in IMAGE_FIELDS:
            return self.structured(ntype, name, key) if ntype == "SliderImageData" else self.photos.photo()
        if need.get("item_fields"):
            return self.items(need, key)
        shaped = self.structured(ntype, name, key)
        if shaped is not None:
            return shaped
        value = self.sample.get(key)
        if ntype == "string[]":
            return value if isinstance(value, list) and all(isinstance(v, str) for v in value) else \
                [f"Sample {name} one", f"Sample {name} two", f"Sample {name} three"]
        if ntype == "number":
            return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 1
        if ntype == "boolean":
            return bool(value)
        if name == "mapEmbedUrl":
            return "https://www.google.com/maps?q=Lahore&output=embed"
        if isinstance(value, str) and value:
            return self.fill(value)
        return f"Sample {name}" if need.get("required") else None

    def live(self, need: dict, key: str) -> Any:
        ntype, name = need.get("type", "string"), need["name"]
        if name == "timeSlots":
            return list(TIME_SLOTS)
        shaped = self.structured(ntype, name, key)
        if shaped is not None:
            return shaped
        if need.get("item_fields"):
            return self.items(need, key)
        if name in IMAGE_FIELDS:
            return self.photos.photo()
        if ntype == "string[]":
            return ["Sample", "Tag"]
        return {"date": "December 1, 2026", "readTime": "3 min read", "category": "News",
                "content": "This is sample text for the post. The owner's own words replace it later.",
                }.get(name, f"Sample {name}")

    # ------------------------------------------------------------ one section
    def props(self, section: PlannedComponent) -> dict:
        out: dict[str, Any] = {}
        keys = {need["name"]: key for need, key in section_keys(section, self.specs)}
        for need in needs_of(section, self.specs):
            name, kind = need["name"], need["kind"]
            if name in LEFT_OUT or (kind == "code" and name != "copyright"):
                continue
            if kind == "copy":
                value = self.text(section.section_id, name)
                if value is None and need.get("required"):
                    value = self.business if name in ("title", "headline") else None
            elif kind == "setting":
                value = _setting(need, section.settings.get(name))
                if value is None and name == "links":
                    value = self.nav_links()
                elif value is None and name == "columns" and section.component_id == "footer":
                    value = self.footer_columns()
                elif value is None and name == "breadcrumbs" and section.page in self.pages:
                    page = self.pages[section.page]
                    value = [{"label": "Home", "href": "/"}, {"label": page.title, "isCurrent": True}] \
                        if page.route != "/" else None
                elif value is None and need.get("role") == "link":
                    value = self.link(section, name)
            elif kind == "live":
                value = self.live(need, keys.get(name, name))
            elif kind == "code":
                value = f"© 2026 {self.business}. All rights reserved."
            else:
                value = self.content(need, keys.get(name, name))
            if value is not None:
                out[name] = value
        if section.component_id == "footer":
            out["variant"] = self.plan.direction.footer_variant
        if section.component_id in ("navbar", "footer", "seo-head", "location-map"):
            out.setdefault("brandName" if section.component_id != "location-map" else "businessName", self.business)
        return out

    def fallback(self, section: PlannedComponent) -> tuple[str, dict]:
        """A custom part, until the custom-part writer exists: a plain call-to-action section with its name and
        purpose (D-240)."""
        spec = self.specs.get(section.custom_spec_id or "")
        headline = self.text(section.section_id, "title") or (spec.name if spec else "Coming soon")
        return _name(FALLBACK_PART), {"headline": headline, "subheadline": spec.purpose if spec else "",
                                      "primaryCtaText": "Get in touch", "primaryCtaLink": self.target or "/",
                                      "variant": "panel"}

    def render(self, section: PlannedComponent) -> tuple[str, str]:
        """(component name, JSX line) for one section. A model-written part (custom part or showcase section) gets
        the same props the compiler builds for it; without one, a custom part shows its fallback (D-228, D-230)."""
        part = self.written.get(section.section_id)
        if section.section_id in self.forms:          # a form on a recipe table: the code-built form (D-248)
            return "DataForm", f"<DataForm {{...{_js({'spec': self.forms[section.section_id]})}}} />"
        if part:
            name, props = part["export_name"], self.props(section)
            self.modules[name] = part["module"]
        elif section.custom or not section.component_id:
            name, props = self.fallback(section)
        else:
            name, props = _name(section.component_id), self.props(section)
        return name, f"<{name} {{...{_js(props)}}} />"


# ---------------------------------------------------------------- files
def _imports(names: list[str], modules: dict[str, str] | None = None) -> str:
    return "\n".join(f'import {{ {n} }} from "{(modules or {}).get(n, f"@/components/{n}")}"'
                     for n in sorted(set(names)))


def _wrap(section_id: str, jsx: str) -> str:
    body = "\n".join("      " + line for line in jsx.splitlines())
    return f'    <div id="section-{_suffix(section_id)}" className="scroll-mt-20">\n{body}\n    </div>'


def _page(site: Site, page) -> str:
    rendered = [(sid, *site.render(site.sections[sid])) for sid in page.section_ids if sid in site.sections
                and site.sections[sid].component_id != fixed.SEO[1]]
    title = site.text(f"{page.page_id}.{fixed.SEO[0]}", "title") or f"{page.title} · {site.business}"
    description = site.text(f"{page.page_id}.{fixed.SEO[0]}", "description") or ""
    dynamic = "[" in page.route
    head = 'import type { Metadata } from "next"\n' + _imports([n for _, n, _ in rendered], site.modules)
    meta = f"export const metadata: Metadata = {_js({'title': {'absolute': title}, 'description': description})}"
    body = "\n".join(_wrap(sid, jsx) for sid, _, jsx in rendered)
    if dynamic:
        param = re.search(r"\[(\w+)\]", page.route).group(1)
        return (f"{head}\n\n{meta}\n\nexport function generateStaticParams() {{\n  return [1, 2, 3].map((n) => "
                f"({{ {param}: `sample-post-${{n}}` }}))\n}}\n\nexport default function Page() {{\n  return (\n"
                f"    <>\n{body}\n    </>\n  )\n}}\n")
    return f"{head}\n\n{meta}\n\nexport default function Page() {{\n  return (\n    <>\n{body}\n    </>\n  )\n}}\n"


def _page_path(route: str) -> str:
    clean = route.strip("/")
    return "app/page.tsx" if not clean else f"app/{clean}/page.tsx"


def _layout(site: Site) -> str:
    d, theme = site.plan.direction, site.plan.theme or {}
    wide = [c for c in site.plan.components if c.page == "all" and c.component_id not in (None, "not-found-page")]
    top = [c for c in wide if c.component_id == "navbar"]
    rest = [c for c in wide if c.component_id != "navbar"]
    rendered_top = [site.render(c) for c in top]
    rendered_rest = [site.render(c) for c in sorted(rest, key=lambda c: c.component_id != "footer")]
    fonts = theme.get("fonts") or {}
    families = sorted({fonts.get("heading") or DEFAULT_FONT, fonts.get("body") or DEFAULT_FONT})
    font_url = "https://fonts.googleapis.com/css2?" + "&".join(
        f"family={f.replace(' ', '+')}:wght@400;500;600;700" for f in families) + "&display=swap"
    home_title = site.text(f"home.{fixed.SEO[0]}", "title") or site.business
    meta = {"title": {"default": home_title, "template": f"%s · {site.business}"},
            "description": site.text(f"home.{fixed.SEO[0]}", "description") or ""}
    dark = ' className="dark"' if theme.get("default_mode") == "dark" else ""
    attrs = (f'data-density="{d.density}" data-corners="{d.corners}" data-type="{d.type_scale}" '
             f'data-surfaces="{d.surfaces}" data-rhythm="{d.rhythm}" data-images="{d.images}" '
             f'data-headings="{d.headings}"')
    indent = lambda jsx: "\n".join("        " + line for line in jsx.splitlines())
    return f'''import type {{ Metadata }} from "next"
import "./globals.css"
{_imports([n for n, _ in rendered_top + rendered_rest], site.modules)}

// Written by FORGE's frontend agent (D-240) from the approved plan: theme, design direction and site-wide parts.
export const metadata: Metadata = {_js(meta)}

export default function RootLayout({{ children }}: Readonly<{{ children: React.ReactNode }}>) {{
  return (
    <html lang="en"{dark}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href="{font_url}" />
      </head>
      <body className="min-h-screen antialiased" {attrs}>
        <p role="note" className="bg-muted px-4 py-1.5 text-center text-xs text-muted-foreground">
          Sample content: your own details, photos and prices replace it before the site goes live.
        </p>
{chr(10).join(indent(jsx) for _, jsx in rendered_top)}
        <main>{{children}}</main>
{chr(10).join(indent(jsx) for _, jsx in rendered_rest)}
      </body>
    </html>
  )
}}
'''


def _globals(site: Site, template_css: str) -> str:
    theme = site.plan.theme or {}
    fonts = theme.get("fonts") or {}
    radius = theme.get("radius") or DEFAULT_RADIUS
    block = lambda sel, tokens, extra="": (f"{sel} {{\n{extra}" + "".join(f"  --{k}: {v};\n" for k, v in tokens.items())
                                          + "}\n")
    root = block(":root", site.light, f"  --radius: {radius};\n") if site.light else None
    css = re.sub(r":root\s*\{[^}]*\}\n?", root, template_css, count=1) if root else template_css
    heading, body = fonts.get("heading") or DEFAULT_FONT, fonts.get("body") or DEFAULT_FONT
    css += ("\n/* Written by FORGE's frontend agent (D-240): the theme's dark colours and fonts. */\n"
            + (block(".dark", site.dark) if site.dark else "")
            + f'@layer base {{\n  body {{ font-family: "{body}", ui-sans-serif, system-ui, sans-serif; }}\n'
            f'  h1, h2, h3, h4 {{ font-family: "{heading}", ui-sans-serif, system-ui, sans-serif; }}\n}}\n')
    return css


def _not_found(site: Site) -> str:
    part = next((c for c in site.plan.components if c.component_id == "not-found-page"), None)
    props = site.props(part) if part else {"title": "Page not found", "homeHref": "/"}
    return (f'import {{ NotFoundPage }} from "@/components/NotFoundPage"\n\nexport default function NotFound() {{\n'
            f"  return <NotFoundPage {{...{_js(props)}}} />\n}}\n")


def _sitemap(site: Site) -> str:
    routes = [p.route for p in site.plan.pages if "[" not in p.route]
    return ('import type { MetadataRoute } from "next"\n\nconst base = process.env.NEXT_PUBLIC_SITE_URL ?? '
            '"https://example.com"\n\nexport default function sitemap(): MetadataRoute.Sitemap {\n  return '
            f"{_js(routes)}.map((route) => ({{ url: `${{base}}${{route}}` }}))\n}}\n")


ROBOTS = ('import type { MetadataRoute } from "next"\n\nconst base = process.env.NEXT_PUBLIC_SITE_URL ?? '
          '"https://example.com"\n\nexport default function robots(): MetadataRoute.Robots {\n'
          '  return { rules: { userAgent: "*", allow: "/" }, sitemap: `${base}/sitemap.xml` }\n}\n')


def compile_site(plan: BuildPlan, business_type: str | None = None, seed: str = "",
                 written: dict | None = None) -> dict[str, str]:
    """The site's own files, by path. Overlaid on site_template/ and the catalogue by the build worker. `written`
    = the model-written parts that passed the gate (section id -> {"module", "export_name"}); their own files are
    added by the caller."""
    from agents.build_worker import TEMPLATE
    site = Site(plan, business_type, seed or business_type or "site", written)
    files = {_page_path(p.route): _page(site, p) for p in plan.pages}
    files["app/layout.tsx"] = _layout(site)
    files["app/globals.css"] = _globals(site, (TEMPLATE / "app" / "globals.css").read_text(encoding="utf-8"))
    files["app/not-found.tsx"] = _not_found(site)
    files["app/sitemap.ts"] = _sitemap(site)
    files["app/robots.ts"] = ROBOTS
    if site.forms:                                       # what each form may send, checked by the site's routes (D-248)
        from agents.backend_generator.agent import schemas_ts
        files["lib/schemas.ts"] = schemas_ts(site.forms)
    files["content/site.json"] = _js({"business_name": site.business, "sample_content": True,
                                      "menu": site.nav_links(), "direction_preset": plan.direction_preset}) + "\n"
    return dict(sorted(files.items()))


def input_summary(plan: BuildPlan, business_type: str | None = None) -> dict:
    """What the frontend agent receives, for the studio's "what the frontend agent received" panel."""
    by_id = {c.section_id: c for c in plan.components}
    theme = plan.theme or {}
    return {
        "business_type": business_type,
        "pages": [{"title": p.title, "route": p.route, "sections": [
            {"section": s, "component": by_id[s].component_id or "custom part",
             "variant": by_id[s].settings.get("variant")} for s in p.section_ids if s in by_id
            and by_id[s].component_id != fixed.SEO[1]]} for p in plan.pages],
        "site_wide": [c.component_id for c in plan.components if c.page == "all"],
        "direction": {"preset": plan.direction_preset, **plan.direction.model_dump(exclude={"chosen"})},
        "theme": {"fonts": theme.get("fonts"), "primary": ((theme.get("tokens") or {}).get("light") or {}).get("primary"),
                  "mode": theme.get("default_mode", "light")},
        "texts": len(plan.texts), "content_fields": len(plan.content_schema),
    }
