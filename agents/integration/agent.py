# D:\FYP\FORGE-1\agents\integration\agent.py
"""
The Integration Agent (D-252 - D-254): the last builder step. It waits for the database, backend and frontend parts,
joins them into one site, checks by code that they fit (I1-I12), and saves the site's manifest. No model call.
"""
import json
from typing import Callable

from agents.file_store import active_store
from agents.integration.checks import failures, run_checks
from agents.integration.join import JoinError, join, manifest_json
from agents.state import AgentArtifacts, BuildPlan

PARTS = ("database", "backend", "frontend")


def run(plan: BuildPlan, request_id: str, artifacts: dict[str, AgentArtifacts],
        progress: Callable[[dict], None]) -> AgentArtifacts:
    def say(message: str, **extra) -> None:
        progress({"agent": "integration", "message": message, **extra})

    say("Integration: joining the database, backend and frontend into one site")
    broken = [a for a in PARTS if a in artifacts and artifacts[a].status == "failed"]
    stored = active_store().read(request_id)
    parts, model_paths, seen = {}, set(), {}
    try:
        for agent in PARTS:
            for ref in artifacts.get(agent, AgentArtifacts(agent=agent)).files:
                if ref.path in seen and seen[ref.path][1] != ref.sha256:      # the store keeps one copy per path
                    raise JoinError(f"FORGE bug: the {seen[ref.path][0]} and {agent} parts wrote {ref.path} differently")
                seen[ref.path] = (agent, ref.sha256)
                parts.setdefault(agent, {})[ref.path] = stored[ref.path]
                if ref.written_by == "model":
                    model_paths.add(ref.path)
        files, manifest = join(parts, model_paths)
    except JoinError as error:
        say(f"Integration: {error}. This is a FORGE bug, not yours.")
        return AgentArtifacts(agent="integration", status="failed")

    checks = run_checks(files, plan, model_paths)
    bad = failures(checks)
    summary = {"checks": [c.__dict__ for c in checks], "passed": len(checks) - len(bad), "total": len(checks),
               "failed_parts": broken}
    say(f"Integration: {len(parts)} part{'s' if len(parts) != 1 else ''} joined, "
        f"{len(checks) - len(bad)}/{len(checks)} links checked")
    for c in bad[:3]:
        say(f"Integration: {c.message}")
    live = _live(plan, request_id, files, artifacts, say) if not bad and not broken else None
    if live:
        summary["live"] = [{"step": w, "ok": ok, "detail": d} for w, ok, d in live.steps]
    refs = active_store().put(request_id, {".env.example": files[".env.example"],
                                           "forge/manifest.json": manifest_json(manifest, summary),
                                           "forge/integration.json": json.dumps(summary, indent=2)},
                              "code", kind="integration")
    if broken:
        say(f"Integration: the {' and '.join(broken)} part{'s' if len(broken) > 1 else ''} did not finish, "
            "so the site is not complete")
    ok = not bad and not broken and (live is None or live.ok)
    say("Your site is ready" if ok else "Stopped. This is a FORGE bug, not yours: the team has the error above.")
    return AgentArtifacts(agent="integration", status="done" if ok else "failed", files=refs)


def _live(plan: BuildPlan, request_id: str, files: dict[str, str], artifacts: dict, say):
    """The live check (D-254) when the site has storage and a running preview with its key; else None."""
    from agents import preview
    from agents.backend_generator.gate import sample_payload
    from agents.database_generator.agent import database_url
    from agents.database_generator.seed import seed_rows
    from agents.integration.live import check_live

    running, contract = preview.get(request_id), json.loads(files.get("db/schema.json") or "{}")
    forms = json.loads(files.get("lib/forms.json") or "{}")
    database = artifacts.get("database")
    if not (running and preview.site_key(request_id) and forms and contract.get("schema")
            and database and database.status == "done"):
        return None
    tz = contract.get("time_zone") or "Asia/Karachi"
    rows = seed_rows(plan.data_entities, tz)
    say("Integration: trying your forms through the site itself")
    result = check_live(running.local_url, forms, {t["name"]: t for t in contract["tables"]}, contract["schema"],
                        database_url(), lambda spec: sample_payload(spec, rows, plan), tz)
    for what, ok, detail in result.steps:
        if not ok:
            say(f"Integration: {what}: failed ({detail})")
    if result.ok:
        say(f"Integration: {result.saved} test submission{'s' if result.saved != 1 else ''} saved through your site, "
            "then removed")
    return result
