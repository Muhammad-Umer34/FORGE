# D:\FYP\FORGE-1\scripts\run_builder_eval.py
"""
Builder evaluation (Phase 3 item 3.8): how often the Frontend Agent turns an approved plan into a site that builds.

    python scripts/run_builder_eval.py                 # plan (once, cached) and build all 8 requests
    python scripts/run_builder_eval.py --only b-rest-02 --replan

Each request in scripts/builder_briefs.json is planned with the strict simulated owner (as in run_eval.py) and the
plan is saved in scripts/runs/builder_plans/, so a rebuild costs no planning calls. Then the site is built with the
gate on and no preview. Per site: the outcome (built first time / after fixes / with fallbacks / failed), custom parts
written, fix rounds, files written by code vs by the model, time and cost. Results go to
scripts/runs/builder_eval_<time>.json, rows saved before the summary (a summary bug never loses a run).
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from agents.frontend_generator import agent  # noqa: E402
from agents.state import BuildPlan, RunConfig  # noqa: E402

BRIEFS = ROOT / "scripts" / "builder_briefs.json"
PLANS = ROOT / "scripts" / "runs" / "builder_plans"
OUT = ROOT / "scripts" / "runs"
PARTS = OUT / "builder_parts"         # model-written files of each site
BUDGET_PER_SITE_USD = 0.50            # PLACEHOLDER: custom parts + fix rounds for one site


async def plan_for(brief: dict) -> tuple[BuildPlan | None, str | None, float, str]:
    """(plan, business type, planning cost, why it failed) with the strict simulated owner."""
    import run_eval as ev
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    from agents.orchestrator import build_forge_graph
    from agents.state import msgpack_allowlist
    captured: dict = {}
    original = ev.measure

    def keep(b, values, seconds, error):
        captured.update(values)
        return original(b, values, seconds, error)

    ev.measure = keep
    graph = build_forge_graph().compile(
        checkpointer=InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist())))
    row = await ev.run_one(graph, brief, 1)
    ev.measure = original
    if row["outcome"] != "planned" or not captured.get("plan"):
        return None, None, row["cost_usd"], f"{row['outcome']}: {row.get('error') or row.get('failure')}"
    brief_obj = captured.get("brief")
    return captured["plan"], brief_obj.business_type if brief_obj else None, row["cost_usd"], ""


def outcome(stats: dict) -> str:
    if stats.get("status") != "done":
        return "failed"
    if stats["fallbacks"] or stats["write_failures"]:
        return "with fallbacks"
    return "after fixes" if stats["rounds"] or stats["code_fixes"] else "first time"


def build_one(brief: dict, plan: BuildPlan, business: str | None) -> dict:
    stats, lines = {}, []
    started = time.perf_counter()
    artifacts, usage = agent.run(plan, business, f"beval-{brief['id']}", RunConfig(preview=False, build_gate=True),
                                 lambda e: lines.append(e.get("message", "")), BUDGET_PER_SITE_USD, stats)
    from agents.file_store import active_store       # keep what the model wrote, for review and the report
    saved = active_store().read(f"beval-{brief['id']}")
    for ref in artifacts.files:
        if ref.written_by == "model":
            target = PARTS / brief["id"] / ref.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(saved[ref.path], encoding="utf-8")
    row = {"id": brief["id"], "group": brief["group"], "custom_request": brief.get("custom", False),
           "outcome": outcome(stats), "seconds": round(time.perf_counter() - started, 1),
           "build_cost_usd": round(usage.estimated_cost_usd, 4), "model_calls": usage.calls,
           "custom_specs": [s.name for s in plan.custom_specs],
           "showcase": [c.section_id for c in plan.components if c.showcase], **stats, "log": lines}
    print(f"  {brief['id']}: {row['outcome']}, parts {stats['in_site']}/{stats['parts']}, rounds {stats['rounds']}, "
          f"{row['seconds']} s, ${row['build_cost_usd']:.3f}", flush=True)
    return row


def summary(rows: list[dict]) -> dict:
    built = [r for r in rows if "outcome" in r]
    count = lambda o: sum(1 for r in built if r["outcome"] == o)
    parts = sum(r["parts"] for r in built)
    return {
        "sites": len(built), "built": len(built) - count("failed"),
        "first_time": count("first time"), "after_fixes": count("after fixes"),
        "with_fallbacks": count("with fallbacks"), "failed": count("failed"),
        "custom_parts": parts, "custom_parts_in_site": sum(r["in_site"] for r in built),
        "fix_rounds": sum(r["rounds"] for r in built), "code_fixes": sum(r["code_fixes"] for r in built),
        "check_rounds": sum(r.get("check_rounds", 0) for r in built),
        "model_files": sum(r["model_files"] for r in built), "code_files": sum(r["code_files"] for r in built),
        "share_written_by_code": round(sum(r["code_files"] for r in built)
                                       / max(1, sum(r["code_files"] + r["model_files"] for r in built)), 3),
        "avg_seconds": round(sum(r["seconds"] for r in built) / max(1, len(built)), 1),
        "avg_build_cost_usd": round(sum(r["build_cost_usd"] for r in built) / max(1, len(built)), 4),
        "planning_failures": [r["id"] for r in rows if "outcome" not in r],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--only", default="", help="comma-separated request ids")
    parser.add_argument("--replan", action="store_true", help="plan again even when a saved plan exists")
    args = parser.parse_args()
    wanted = {i.strip() for i in args.only.split(",") if i.strip()}
    briefs = [b for b in json.loads(BRIEFS.read_text(encoding="utf-8"))["briefs"] if not wanted or b["id"] in wanted]
    PLANS.mkdir(parents=True, exist_ok=True)
    rows = []
    out = OUT / f"builder_eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    for brief in briefs:
        saved = PLANS / f"{brief['id']}.json"
        if saved.exists() and not args.replan:
            data = json.loads(saved.read_text(encoding="utf-8"))
            plan, business, plan_cost = BuildPlan.model_validate(data["plan"]), data["business_type"], 0.0
        else:
            print(f"Planning {brief['id']}...", flush=True)
            plan, business, plan_cost, why = asyncio.run(plan_for(brief))
            if plan is None:
                print(f"  {brief['id']}: planning did not end with a plan ({why})", flush=True)
                rows.append({"id": brief["id"], "group": brief["group"], "planning_failed": why})
                continue
            saved.write_text(json.dumps({"business_type": business, "plan": plan.model_dump(mode="json")}, indent=2),
                             encoding="utf-8")
        row = build_one(brief, plan, business)
        row["planning_cost_usd"] = plan_cost
        rows.append(row)
        out.write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "rows": rows}, indent=2),
                       encoding="utf-8")
    result = {"at": datetime.now(timezone.utc).isoformat(), "rows": rows}
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")       # rows first, then the summary
    result["summary"] = summary(rows)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("\nSUMMARY\n" + json.dumps(result["summary"], indent=2) + f"\nSaved to: {out}")


if __name__ == "__main__":
    main()
