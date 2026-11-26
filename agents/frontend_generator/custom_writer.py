# D:\FYP\FORGE-1\agents\frontend_generator\custom_writer.py
"""
The custom-part writer (D-228): the only code in a generated site that a model writes.

A custom part is a feature our 49-part library cannot build (a loyalty stamp card, a price calculator); a showcase
section is one the planner marked to be written fresh for this business (D-224). Everything a writer could get wrong
by guessing is fixed by code first:
- the file path and export name come from the plan (`CustomComponentSpec.file`, `.export_name`);
- the props interface is written by code from the part's needs, and the page passes exactly those props, so the page
  type-checks against the part before the part exists (a showcase section keeps its library part's props type);
- every prompt is rendered from the plan (spec, props, sample values, design direction, a library section as a style
  reference), never from the chat.
One call per part, at most 3 at once (`gateway.call_files_parallel`); the spending cap counts calls still running.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from agents.build_worker import CATALOGUE, TEMPLATE
from agents.frontend_generator.compiler import LEFT_OUT, Site, _name
from agents.gateway import CallUsage, call_files_parallel
from agents.planning.assemble import custom_file
from agents.planning.content_schema import load_needs, needs_of
from agents.state import BuildPlan, PlannedComponent

TASK = "frontend_custom"
REFERENCE_LIMIT = 6000                       # characters of library source shown as a style reference
_TS_TYPE = {"number": "number", "boolean": "boolean"}   # every other field type is a string (text, money, url, image…)


@dataclass
class Part:
    """One model-written part and the contract code fixed for it."""
    section_id: str
    kind: str                                # "custom" | "showcase"
    name: str                                # what the owner calls it
    file: str                                # components/custom/<id>/<id>.tsx
    export_name: str
    props_code: str                          # the interface to copy, or the import of the library props type
    sample_props: dict = field(default_factory=dict)
    brief: str = ""                          # the user prompt

    @property
    def folder(self) -> str:
        return self.file.rsplit("/", 1)[0] + "/"

    @property
    def module(self) -> str:
        return "@/" + self.file.removesuffix(".tsx")


# ---------------------------------------------------------------- props fixed by code
def _ident(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_$][\w$]*", name) else json.dumps(name)


def _field_type(need: dict) -> str:
    if need.get("item_fields"):
        inner = "; ".join(f"{_ident(f['name'])}?: {_field_type(f)}" for f in need["item_fields"]
                          if "=>" not in str(f.get("type", "")))
        return f"{{ {inner} }}[]"
    return _TS_TYPE.get(str(need.get("type")), "string")


def props_interface(name: str, needs: list[dict]) -> str:
    """The props of a custom part, from its needs, in the form the compiler fills them (`Site.props`). Every prop is
    optional: the part gives defaults, so a missing sample never breaks the build."""
    lines = [f"  {_ident(n['name'])}?: {_field_type(n)}" for n in needs
             if n.get("kind") != "code" and n["name"] not in LEFT_OUT]
    return f"export interface {name}Props {{\n" + "\n".join(lines) + "\n}"


# ---------------------------------------------------------------- what to write
def _ui_exports() -> str:
    out = []
    for f in sorted((TEMPLATE / "components" / "ui").glob("*.tsx")):
        names = re.findall(r"^export (?:function|const) (\w+)", f.read_text(encoding="utf-8"), re.M)
        names += [n.strip() for block in re.findall(r"^export \{([^}]*)\}", f.read_text(encoding="utf-8"), re.M)
                  for n in block.split(",") if n.strip()]
        out.append(f"@/components/ui/{f.stem}: {', '.join(n for n in names if not n.endswith('Variants'))}")
    return "\n".join(out)


def _reference(plan: BuildPlan, section: PlannedComponent) -> str:
    """A library section from the same page as a style reference: the part should look like it belongs."""
    near = [c.component_id for c in plan.components
            if c.page == section.page and c.component_id and not c.custom and c.component_id != "hero-banner"]
    for cid in near + ["features-grid"]:
        entry = load_needs().get(cid)
        if entry and (CATALOGUE / entry["file"]).exists():
            return (CATALOGUE / entry["file"]).read_text(encoding="utf-8")[:REFERENCE_LIMIT]
    return ""


def parts_to_write(plan: BuildPlan, site: Site) -> list[Part]:
    """Every custom part and showcase section of the plan, with its contract and prompt."""
    d, out = plan.direction, []
    style = (f"density {d.density}, corners {d.corners}, type {d.type_scale}, surfaces {d.surfaces}, "
             f"sections {d.rhythm}, images {d.images}, headings {d.headings}")
    for c in plan.components:
        if c.custom and c.custom_spec_id in site.specs:
            spec = site.specs[c.custom_spec_id]
            props = props_interface(spec.export_name, needs_of(c, site.specs))
            part = Part(c.section_id, "custom", spec.name, spec.file, spec.export_name, props, site.props(c))
            task = (f"Part: {spec.name}\nWhat it is for: {spec.purpose}\nWhat it must do:\n"
                    + "".join(f"- {b}\n" for b in spec.behaviour)
                    + (f"Layout notes: {spec.ui_notes}\n" if spec.ui_notes else "")
                    + (f"It is a form that sends: {', '.join(spec.sends)}\n" if spec.sends else ""))
        elif c.showcase and c.component_id in load_needs():
            entry = load_needs()[c.component_id]
            file, export = custom_file(f"showcase-{c.section_id.replace('.', '-')}")
            props = f'import type {{ {entry["props"]} }} from "@/components/{entry["file"].removesuffix(".tsx")}"'
            part = Part(c.section_id, "showcase", f"{_name(c.component_id)} (showcase)", file, export, props,
                        site.props(c))
            task = (f"Write a fresh, more distinctive version of the library section {_name(c.component_id)} for "
                    f"this business. Why: {c.showcase}\nTake the same props: {entry['props']}.\n")
        else:
            continue
        part.brief = (f"{task}\nFile to write: {part.file}\nExport: export function {part.export_name}\n"
                      f"Props (use exactly this):\n```ts\n{part.props_code}\n```\n"
                      f"Props the page will pass:\n```json\n{json.dumps(part.sample_props, indent=2)[:3000]}\n```\n"
                      f"Design direction of this site: {style}\n"
                      f"A library section of this site, for style only (do not import it):\n```tsx\n"
                      f"{_reference(plan, c)}\n```")
        out.append(part)
    return out


SYSTEM = """You write one React component for a small-business website: Next.js 16 (App Router), React 19, TypeScript,
Tailwind CSS 4. Rules:
- Write exactly one file, at the path given, with a named export `export function <Export>(props)` (no default export).
- Use the props given exactly: copy the interface into the file unchanged, or keep the import type line as given.
  Every prop may be missing: give sensible defaults so the part renders with no props.
- Put "use client" on the first line only if you use state, effects or event handlers.
- Style with Tailwind and the site's theme tokens only: bg-background text-foreground bg-card text-card-foreground
  bg-primary text-primary-foreground bg-secondary text-secondary-foreground bg-muted text-muted-foreground bg-accent
  text-accent-foreground border-border ring-ring; rounded-md, rounded-lg or rounded-xl (the site sets the radius).
  Never raw colours: no gray-500, no blue-600, no hex values.
- Imports allowed: react; next/link; lucide-react icons; @/lib/utils (cn); these interface parts:
{ui}
  Nothing else: no other custom part, no next/image (use <img>), no network calls (no fetch, no /api/ paths,
  no process.env), no external URLs.
- A part that sends something is a form: labelled fields and, on submit, a thank-you message. It sends nothing yet.
- Accessible: semantic HTML, a label for every input, alt text on images, buttons with visible text. Anything
  clickable is a <button type="button"> or a checkbox <input> with a <label>, never a <div onClick>: a keyboard
  cannot reach a div.
- Lay it out like the site's other sections: <section className="py-16"><div className="mx-auto max-w-6xl px-6">;
  one h2 heading, never an h1.
- Keep it under about 250 lines."""


def system_prompt() -> str:
    return SYSTEM.replace("{ui}", "\n".join(f"  {line}" for line in _ui_exports().splitlines()))


# ---------------------------------------------------------------- write and accept
def accept(part: Part, files: dict[str, str]) -> tuple[dict[str, str] | None, str]:
    """The part's files if they keep to the contract, else (None, why)."""
    outside = [p for p in files if not p.startswith(part.folder)]
    if outside:
        return None, f"wrote outside its folder: {', '.join(outside)}"
    main = files.get(part.file)
    if main is None:
        return None, f"did not write {part.file}"
    if not re.search(rf"export\s+(?:function|const)\s+{part.export_name}\b", main):
        return None, f"does not export {part.export_name}"
    from agents.integration.checks import FORBIDDEN_IN_MODEL_PARTS      # integration check I9, enforced here first
    for path, text in files.items():
        if hit := FORBIDDEN_IN_MODEL_PARTS.search(text):
            return None, f"{path} uses '{hit.group(0)}': only FORGE's own forms may reach the API"
    return files, ""


def write_parts(parts: list[Part], budget_usd: float) -> list[tuple[Part, dict[str, str] | None, str, CallUsage]]:
    """All parts at once (at most 3 calls running). Each result: the accepted files, or None and the reason."""
    system = system_prompt()
    results = call_files_parallel([(TASK, system, p.brief) for p in parts], budget_usd)
    out = []
    for part, (files, usage) in zip(parts, results):
        if isinstance(files, Exception):
            out.append((part, None, f"{type(files).__name__}: {files}"[:300], usage))
            continue
        accepted, why = accept(part, files)
        out.append((part, accepted, why, usage))
    return out
