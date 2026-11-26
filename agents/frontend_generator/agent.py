# D:\FYP\FORGE-1\agents\frontend_generator\agent.py
"""The frontend agent's run (D-240, D-228 - D-230): what happens after the owner approves the plan. Each step sends a
progress event to the studio (message, and `input`, `url` or `file` where it has one):
1. the input it received (a summary of the plan);
2. compile the site from the plan by code (library parts, layout, theme, pages);
3. live preview (if on): start `next dev` with the theme and layout, then write the pages one by one;
4. custom parts and showcase sections: written by the model, at most 3 at once, cleaned by the post-processors;
5. gate: type check and production build, with code fixes, model fix rounds and fallbacks for the model's parts;
6. save every file (code-made and model-written marked apart).
Model-written code only enters a site through the gate: with the gate off (tests, quick runs) custom parts keep their
fallback section and no model is called."""
from typing import Callable

from agents import preview
from agents.file_store import active_store
from agents.frontend_generator.compiler import Site, compile_site, input_summary
from agents.frontend_generator.custom_writer import Part, parts_to_write, write_parts
from agents.frontend_generator.gate import run_gate
from agents.frontend_generator.postprocess import postprocess
from agents.gateway import CallUsage
from agents.state import AgentArtifacts, BuildPlan, RunConfig, UsageSummary

BUILDING_PAGE = ('export default function Page() {\n  return (\n    <section className="mx-auto max-w-2xl px-6 py-24 '
                 'text-center">\n      <p className="text-sm text-muted-foreground">FORGE is writing your site…</p>\n'
                 '    </section>\n  )\n}\n')


def _total(usages: list[CallUsage]) -> UsageSummary:
    return UsageSummary(calls=sum(u.calls for u in usages), prompt_tokens=sum(u.prompt_tokens for u in usages),
                        completion_tokens=sum(u.completion_tokens for u in usages),
                        unknown_token_calls=sum(u.unknown_token_calls for u in usages),
                        total_latency_ms=sum(u.latency_ms for u in usages),
                        estimated_cost_usd=round(sum(u.cost_usd for u in usages), 6))


def run(plan: BuildPlan, business_type: str | None, request_id: str, config: RunConfig,
        progress: Callable[[dict], None], budget_usd: float = 1.0,
        report: dict | None = None) -> tuple[AgentArtifacts, UsageSummary]:
    """`report`, when given, is filled with the run's numbers (the builder evaluation reads them)."""
    say = lambda message, **extra: progress({"stage": "frontend", "message": message, **extra})
    summary = input_summary(plan, business_type)
    sections = sum(len(p["sections"]) for p in summary["pages"])
    fonts = (summary["theme"].get("fonts") or {}).get("heading") or "Inter"
    say(f"Frontend agent received the plan: {len(plan.pages)} pages, {sections} sections, "
        f"direction {plan.direction_preset or 'chosen'}, font {fonts}", input=summary)

    parts = parts_to_write(plan, Site(plan, business_type, request_id)) if config.build_gate else []
    files = compile_site(plan, business_type, request_id)
    say(f"Wrote {len(files)} files from the plan, no model call needed"
        + (f"; {len(parts)} custom part{'s' if len(parts) > 1 else ''} to write with AI" if parts else ""))
    live = _preview(plan, files, request_id, say) if config.preview else None

    usages: list[CallUsage] = []
    part_files: dict[str, dict[str, str]] = {}
    if parts:
        say(f"Writing {len(parts)} custom part{'s' if len(parts) > 1 else ''} with AI, up to 3 at a time")
        for part, accepted, why, usage in write_parts(parts, budget_usd):
            usages.append(usage)
            if accepted:
                part_files[part.section_id], fixes, _ = postprocess(accepted, part.folder)
                say(f"Wrote {part.name} (AI)" + (f", {len(fixes)} small fixes by code" if fixes else ""))
            else:
                say(f"Could not write {part.name} ({why}); a plain section takes its place")
    written = {p.section_id: p for p in parts if p.section_id in part_files}
    stats = report if report is not None else {}
    stats.update(parts=len(parts), written=len(written), write_failures=len(parts) - len(written), rounds=0, check_rounds=0,
                 code_fixes=0, fallbacks=[], builds=0, gate_message="")

    def compile_with(keep: dict[str, Part]) -> dict[str, str]:
        return compile_site(plan, business_type, request_id,
                            {sid: {"module": p.module, "export_name": p.export_name} for sid, p in keep.items()})

    if live and written:
        files = compile_with(written)
        live.write({**files, **{p: c for f in part_files.values() for p, c in f.items()}})
        say("Custom parts added to the live preview")

    status, model_paths = "done", set()
    if config.build_gate:
        say("Checking the site: type check, then a production build")
        spent = sum(u.cost_usd for u in usages)
        g = run_gate(compile_with, written, {sid: part_files[sid] for sid in written}, budget_usd - spent, say,
                     build_id=f"gate-{request_id[-12:]}")
        usages += g.usage
        files = g.files
        stats.update(rounds=g.rounds, check_rounds=g.check_rounds, code_fixes=g.code_fixes, builds=g.builds, gate_message=g.message,
                     fallbacks=[f"{name}: {why}" for name, why in g.fallbacks])
        model_paths = {p for sid in g.written for p in files if p.startswith(g.written[sid].folder)}
        if g.ok:
            say(f"Type check and production build passed ({g.builds} build{'s' if g.builds > 1 else ''}"
                + (f", {g.rounds} fix round{'s' if g.rounds > 1 else ''}" if g.rounds else "")
                + (f", {g.code_fixes} fixed by code" if g.code_fixes else "") + ")")
        else:
            status = "failed"
            say(g.message)
            say("The site did not build. This is a FORGE bug, not yours: the team has the error above.")
        if live and (g.fallbacks or g.rounds or g.code_fixes):
            live.write(files)

    store = active_store()
    refs = store.put(request_id, {"forge/plan.json": plan.model_dump_json(indent=2),
                                  **{p: c for p, c in files.items() if p not in model_paths}}, "code")
    if model_paths:
        refs += store.put(request_id, {p: files[p] for p in sorted(model_paths)}, "model")
    stats.update(status=status, model_files=len(model_paths), code_files=len(files) - len(model_paths),
                 in_site=sum(1 for p in written.values() if any(m.startswith(p.folder) for m in model_paths)))
    say("Frontend: done" if status == "done" else "Frontend: stopped")   # "ready" comes after integration
    return AgentArtifacts(agent="frontend", status=status, files=refs), _total(usages)


def _preview(plan: BuildPlan, files: dict[str, str], request_id: str, say: Callable) -> "preview.Preview | None":
    """Start the dev server with the theme and layout, then write each page so the open preview fills in."""
    say("Starting the live preview")
    first = {p: c for p, c in files.items() if not p.startswith("app/") or p in ("app/globals.css", "app/layout.tsx")}
    try:
        live = preview.start(request_id, {**first, "app/page.tsx": BUILDING_PAGE})
    except preview.PreviewError as error:
        say(f"The live preview could not start ({error}). The site is still written.")
        return None
    say("Live preview is running", url=live.url)
    by_route = {("app/page.tsx" if not p.route.strip("/") else f"app/{p.route.strip('/')}/page.tsx"): p
                for p in plan.pages}
    for path, page in by_route.items():
        live.write({path: files[path]})
        count = len([s for s in page.section_ids if not s.endswith(".seo")])
        say(f"Writing {page.title} ({page.route}): {count} section{'' if count == 1 else 's'}", file=path)
    live.write({p: c for p, c in files.items() if p not in first and p not in by_route})
    return live
