# D:\FYP\FORGE-1\scripts\frontend_demo.py
"""
Run the frontend agent outside the studio (D-240): the backup for the supervisor demo, and a quick check.

    python scripts/frontend_demo.py --brief booking-01        # plan one evaluation brief live, then build it
    python scripts/frontend_demo.py --plan scripts/runs/plan_booking-01.json

Prints every progress event, keeps the live preview running until Ctrl+C. With --brief, the approved plan is saved
to scripts/runs/plan_<id>.json so the same plan can be built again without model calls.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from agents import preview  # noqa: E402
from agents.frontend_generator import agent  # noqa: E402
from agents.state import BuildPlan, RunConfig  # noqa: E402


def _show(event: dict) -> None:
    line = f"  {event.get('message', '')}"
    if event.get("url"):
        line += f"\n    -> open {event['url']}"
    print(line, flush=True)


async def plan_for(brief_id: str) -> tuple[BuildPlan, str | None]:
    """Run one evaluation brief through clarification and planning with the strict simulated owner."""
    import run_eval as ev
    captured: dict = {}
    original = ev.measure

    def keep(brief, values, seconds, error):
        captured.update(values)
        return original(brief, values, seconds, error)

    ev.measure = keep
    briefs = ev.load_briefs({brief_id})
    if not briefs:
        sys.exit(f"no evaluation brief called {brief_id}")
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    from agents.orchestrator import build_forge_graph
    from agents.state import msgpack_allowlist
    graph = build_forge_graph().compile(
        checkpointer=InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist())))
    row = await ev.run_one(graph, briefs[0], 1)
    if not captured.get("plan") or row["outcome"] != "planned":
        sys.exit(f"the brief did not end with a plan: {row['outcome']} {row.get('error') or row.get('failure')}")
    return captured["plan"], captured["brief"].business_type if captured.get("brief") else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--brief", help="evaluation brief id to plan live, e.g. booking-01")
    parser.add_argument("--plan", help="a saved plan JSON file")
    parser.add_argument("--business", help="business type for photos (with --plan)")
    parser.add_argument("--no-gate", action="store_true", help="skip the type check and production build")
    args = parser.parse_args()
    if args.plan:
        data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        plan, business = BuildPlan.model_validate(data.get("plan", data)), data.get("business_type", args.business)
    elif args.brief:
        print(f"Planning {args.brief} (clarification and planning with the simulated owner)...", flush=True)
        plan, business = asyncio.run(plan_for(args.brief))
        out = ROOT / "scripts" / "runs" / f"plan_{args.brief}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"business_type": business, "plan": plan.model_dump(mode="json")}, indent=2),
                       encoding="utf-8")
        print(f"Plan saved to {out}")
    else:
        parser.error("give --brief or --plan")
    config = RunConfig(preview=True, build_gate=not args.no_gate)
    started = time.perf_counter()
    result, usage = agent.run(plan, business, f"demo-{args.brief or Path(args.plan).stem}", config, _show)
    print(f"Done in {time.perf_counter() - started:.0f} s: {result.status}, {len(result.files)} files, "
          f"{usage.calls} model calls, ${usage.estimated_cost_usd:.3f}")
    if preview.get(f"demo-{args.brief or Path(args.plan).stem}"):
        print("The preview keeps running. Press Ctrl+C to stop it.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            preview.stop_all()


if __name__ == "__main__":
    main()
