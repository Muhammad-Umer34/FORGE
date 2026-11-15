# D:\FYP\FORGE-1\agents\frontend_generator\agent.py
"""The frontend agent's run (D-240): what happens after the owner approves the plan. Each step sends a progress
event to the studio (message, and `input`, `url` or `file` where it has one):
1. the input it received (a summary of the plan);
2. compile the files and save them in the file store;
3. live preview (if on): start `next dev` with the theme and layout, then write the pages one by one;
4. gate (if on): type check and production build on a separate copy. Every file is made by code, so a failure is a
   compiler bug: the run ends with a clear message, no model fix rounds (those come with model-written code)."""
from typing import Callable

from agents import build_worker, preview
from agents.file_store import active_store
from agents.frontend_generator.compiler import compile_site, input_summary
from agents.state import AgentArtifacts, BuildPlan, RunConfig

BUILDING_PAGE = ('export default function Page() {\n  return (\n    <section className="mx-auto max-w-2xl px-6 py-24 '
                 'text-center">\n      <p className="text-sm text-muted-foreground">FORGE is writing your site…</p>\n'
                 '    </section>\n  )\n}\n')


def run(plan: BuildPlan, business_type: str | None, request_id: str, config: RunConfig,
        progress: Callable[[dict], None]) -> AgentArtifacts:
    summary = input_summary(plan, business_type)
    sections = sum(len(p["sections"]) for p in summary["pages"])
    fonts = (summary["theme"].get("fonts") or {}).get("heading") or "Inter"
    progress({"stage": "frontend", "input": summary,
              "message": f"Frontend agent received the plan: {len(plan.pages)} pages, {sections} sections, "
                         f"direction {plan.direction_preset or 'chosen'}, font {fonts}"})

    files = compile_site(plan, business_type, request_id)
    refs = active_store().put(request_id, {"forge/plan.json": plan.model_dump_json(indent=2), **files}, "code")
    progress({"stage": "frontend", "message": f"Wrote {len(files)} files from the plan, no model call needed"})

    if config.preview:
        _preview(plan, files, request_id, progress)

    status = "done"
    if config.build_gate:
        progress({"stage": "frontend", "message": "Checking the site: type check, then a production build"})
        result = build_worker.build(files, build_id=f"gate-{request_id[-12:]}")
        for step in result.steps:
            label = "Type check" if step.name == "typecheck" else "Production build"
            first = f": {step.issues[0].file}:{step.issues[0].line} {step.issues[0].message}" if step.issues else ""
            progress({"stage": "frontend", "message": f"{label} {'passed' if step.ok else 'failed'} "
                                                      f"({step.seconds:.0f} s){'' if step.ok else first}"})
        if not result.ok:
            status = "failed"
            progress({"stage": "frontend", "message": "The site did not build. This is a FORGE bug, not yours: "
                                                      "the team has the error above."})
    progress({"stage": "frontend", "message": "Your site is ready" if status == "done" else "Stopped"})
    return AgentArtifacts(agent="frontend", status=status, files=refs)


def _preview(plan: BuildPlan, files: dict[str, str], request_id: str, progress: Callable[[dict], None]) -> None:
    """Start the dev server with the theme and layout, then write each page so the open preview fills in."""
    progress({"stage": "frontend", "message": "Starting the live preview"})
    first = {p: c for p, c in files.items() if not p.startswith("app/") or p in ("app/globals.css", "app/layout.tsx")}
    try:
        live = preview.start(request_id, {**first, "app/page.tsx": BUILDING_PAGE})
    except preview.PreviewError as error:
        progress({"stage": "frontend", "message": f"The live preview could not start ({error}). The site is "
                                                  f"still written."})
        return
    progress({"stage": "frontend", "message": "Live preview is running", "url": live.url})
    by_route = {("app/page.tsx" if not p.route.strip("/") else f"app/{p.route.strip('/')}/page.tsx"): p
                for p in plan.pages}
    for path, page in by_route.items():
        live.write({path: files[path]})
        count = len([s for s in page.section_ids if not s.endswith(".seo")])
        progress({"stage": "frontend", "file": path,
                  "message": f"Writing {page.title} ({page.route}): {count} section{'' if count == 1 else 's'}"})
    live.write({p: c for p, c in files.items() if p not in first and p not in by_route})
