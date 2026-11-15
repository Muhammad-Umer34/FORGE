# D:\FYP\FORGE-1\scripts\run_eval.py
"""
Run the fixed evaluation set (scripts/eval_briefs.json, D-217) through Clarification and Planning and report the
numbers. A strict simulated owner answers: only what the brief's answer key covers, otherwise "You decide" (or the
recommended option); it confirms the brief and approves the plan. Real Gemini calls are made (uses credits); each
run is traced in Langfuse with the tags "eval" and the brief id when tracing is on.

Run from the FORGE-1 folder:
    .venv\\Scripts\\python.exe scripts\\run_eval.py                    # every brief, 3 runs each
    .venv\\Scripts\\python.exe scripts\\run_eval.py --only booking-01 --runs 1
Results: scripts/runs/eval_<time>.json (gitignored) and a summary table in the terminal.
"""
import argparse
import asyncio
import json
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer  # noqa: E402
from langgraph.types import Command  # noqa: E402

from agents import tracing  # noqa: E402
from agents.clarification import slots  # noqa: E402
from agents.clarification.schemas import UserAnswer  # noqa: E402
from agents.gateway import provider  # noqa: E402
from agents.orchestrator import build_forge_graph  # noqa: E402
from agents.state import Question, RequestInfo, initial_state, msgpack_allowlist  # noqa: E402
from backend.routes.requests import _run_config  # noqa: E402  the same run settings the API uses

BRIEFS = ROOT / "scripts" / "eval_briefs.json"
OUTPUT_DIR = ROOT / "scripts" / "runs"   # gitignored
MAX_TURNS = 20                           # questions + confirmation + plan; more means a loop


def load_briefs(only: set[str] | None = None) -> list[dict]:
    briefs = json.loads(BRIEFS.read_text(encoding="utf-8"))["briefs"]
    return [b for b in briefs if not only or b["id"] in only]


def owner_answer(payload: dict, key: dict) -> dict:
    """The strict simulated owner: answers from the key, never volunteers anything else."""
    q = Question.model_validate({k: v for k, v in payload.items() if k != "type"})
    options = [o.option_id for o in q.options]
    chosen: list[str] = []
    if q.slot == "purpose":
        chosen = [key["purpose"]] if key.get("purpose") in options else []
    elif q.slot == "visitor_actions":
        chosen = [o for o in key.get("visitor_actions", []) if o in options]
    elif q.kind == "D":
        chosen = [key.get("continue_without_unsupported", "yes")]
    elif q.slot == "custom_limit":
        chosen = options[:q.max_selections or len(options)]
    candidates = []
    if chosen:
        candidates.append(UserAnswer(question_id=q.question_id, kind="option", option_ids=chosen))
    if q.allow_you_decide:
        candidates.append(UserAnswer(question_id=q.question_id, kind="you_decide"))
    recommended = [o.option_id for o in q.options if o.recommended] or options[:1]
    candidates.append(UserAnswer(question_id=q.question_id, kind="option", option_ids=recommended))
    for answer in candidates:
        if slots.validate_answer(q, answer) is None:
            return answer.model_dump()
    raise ValueError(f"no valid answer for question {q.text!r}")


def reply(payload: dict, key: dict) -> dict:
    kind = payload.get("type")
    if kind == "question":
        return owner_answer(payload, key)
    if kind == "plan_approval":
        return {"decision": "approve", "change_text": None}
    return {"decision": "confirm"}            # confirmation screen: keep the selected theme


def outcome(values: dict) -> str:
    c, p = values["clarification"], values.get("planning")
    if c.status in ("out_of_scope", "replied"):   # refused, or answered as not a website request
        return "out_of_scope"
    if p is not None and p.status == "done":
        return "planned"
    return "failed"


def measure(brief: dict, values: dict, seconds: float, error: str | None) -> dict:
    c, p, usage = values.get("clarification"), values.get("planning"), values.get("usage")
    plan, frozen = values.get("plan"), values.get("brief")
    result = outcome(values) if c else "failed"
    in_plan = {x.feature_id for x in plan.components} if plan and result == "planned" else set()
    in_brief = {f.id for f in frozen.features} if frozen else set()
    failure = (p.failure if p and p.failure else c.failure if c and c.failure else None)
    return {
        "brief_id": brief["id"], "group": brief["group"], "expect": brief["expect"], "outcome": result,
        "correct": result == brief["expect"],
        "must_found": sorted(set(brief["must"]) & in_plan), "must_missing": sorted(set(brief["must"]) - in_plan),
        "must_not_leaked": sorted(set(brief["must_not"]) & (in_plan | in_brief)),
        "questions": len(c.questions) if c else 0,
        "calls": usage.calls if usage else 0,
        "clarification_calls": c.calls_used if c else 0, "planning_calls": p.calls_used if p else 0,
        "fix_rounds": p.fix_rounds_used if p else 0, "text_rewrites": p.text_rewrites_used if p else 0,
        "final_issues": list(p.issues) if p and result == "failed" else [],
        "pages": len(plan.pages) if plan and result == "planned" else 0,
        "sections": len(plan.components) if plan and result == "planned" else 0,
        "tests": len(frozen.test_cases) if frozen else 0,
        "shape": shape(plan) if plan and result == "planned" else None,
        "family": (p.start_direction or {}).get("family") if p else None,
        "preset": plan.direction_preset if plan and result == "planned" else None,
        "direction_changes": plan.direction_changes if plan and result == "planned" else [],
        "business_type": frozen.business_type if frozen else None,
        "prompt_tokens": usage.prompt_tokens if usage else 0, "completion_tokens": usage.completion_tokens if usage else 0,
        "cost_usd": round(usage.estimated_cost_usd, 4) if usage else 0.0,
        "seconds": round(seconds, 1),
        "failure": {"node": failure.node, "detail": (failure.detail or "")[:300]} if failure else None,
        "error": error,
    }


async def run_one(graph, brief: dict, n: int) -> dict:
    request_id = f"eval_{brief['id']}_{n}_{uuid.uuid4().hex[:6]}"
    config = tracing.run_config(request_id, ("eval", provider(), brief["id"], brief["group"]))
    graph_input = initial_state(
        RequestInfo(request_id=request_id, user_id="eval", project_id="eval", prompt=brief["prompt"],
                    created_at=datetime.now(timezone.utc)),
        config=_run_config(),
    )
    started, error, values = time.perf_counter(), None, {}
    try:
        for _ in range(MAX_TURNS):
            await graph.ainvoke(graph_input, config)
            snapshot = await graph.aget_state(config)
            values = snapshot.values
            if not snapshot.interrupts:
                break
            graph_input = Command(resume=reply(snapshot.interrupts[0].value, brief["answers"]))
        else:
            error = f"still waiting after {MAX_TURNS} turns"
    except Exception as e:   # an outage or a bug is a result too; keep going with the other runs
        error = f"{type(e).__name__}: {e}"[:300]
        values = (await graph.aget_state(config)).values
    row = measure(brief, values, time.perf_counter() - started, error)
    print(f"  {row['brief_id']} #{n}: {row['outcome']}{'' if row['correct'] else ' (WRONG)'}, "
          f"{row['calls']} calls, ${row['cost_usd']:.3f}, {row['seconds']}s")
    return row


def shape(plan) -> dict:
    """What a plan looks like (D-224): its sections as component + variant, and its design direction."""
    sections = sorted(f"{c.component_id}:{c.settings.get('variant', '-')}" for c in plan.components
                      if c.role == "feature" or c.component_id == "hero-banner")
    return {"sections": sections, "direction": plan.direction.model_dump(exclude={"chosen", "footer_variant"}),
            "preset": plan.direction_preset, "changes": [c["field"] for c in plan.direction_changes]}


def _jaccard(a: list, b: list) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


def sameness(a: dict, b: dict, with_variants: bool = True) -> float:
    """0 = nothing alike, 1 = identical. Without variants: which components are used only (what sites were before
    variants and the design direction existed)."""
    if not with_variants:
        return _jaccard([s.split(":")[0] for s in a["sections"]], [s.split(":")[0] for s in b["sections"]])
    direction = direction_match(a, b)
    return round((_jaccard(a["sections"], b["sections"]) + direction) / 2, 3)


VARIED = ("density", "corners", "type_scale", "surfaces", "rhythm", "images", "headings", "hero_variant")


def direction_match(a: dict, b: dict) -> float:
    """Share of the 8 varied choices two plans have in common (D-239); the footer follows the page count, so it is
    left out. Random picking over the menus would give about 0.40."""
    return sum(a["direction"][k] == b["direction"][k] for k in VARIED) / len(VARIED)


def variety_report(rows: list[dict]) -> dict:
    """Direction variety between plans of different briefs: same family vs different families, the most common
    option of each choice, and how often the model changed each choice (D-239)."""
    planned = [r for r in rows if r.get("shape")]
    same, cross = [], []
    for i, a in enumerate(planned):
        for b in planned[i + 1:]:
            if a["brief_id"] != b["brief_id"]:
                (same if a.get("family") and a.get("family") == b.get("family") else cross).append(
                    direction_match(a["shape"], b["shape"]))
    avg = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
    top = {}
    for k in VARIED:
        counts = {}
        for r in planned:
            counts[r["shape"]["direction"][k]] = counts.get(r["shape"]["direction"][k], 0) + 1
        value = max(counts, key=counts.get) if counts else None
        top[k] = {"most_common": value, "share": round(counts[value] / len(planned), 2) if value else None}
    changed = {}
    for r in planned:
        for c in r.get("direction_changes") or []:
            changed[c["field"]] = changed.get(c["field"], 0) + 1
    return {"same_family": {"pairs": len(same), "match": avg(same)},
            "cross_family": {"pairs": len(cross), "match": avg(cross)},
            "all_pairs": {"pairs": len(same) + len(cross), "match": avg(same + cross)},
            "most_common": top,
            "model_change_rate": {k: round(v / len(planned), 2) for k, v in changed.items()} if planned else {},
            "presets_used": len({r.get("preset") for r in planned if r.get("preset")})}


def sameness_report(rows: list[dict]) -> dict:
    """Average sameness of plans for different briefs in the same group (two booking sites...), and of the same
    brief planned twice, with and without variants (P15)."""
    planned = [r for r in rows if r.get("shape")]
    pairs = {"same_group": [], "same_brief": []}
    for i, a in enumerate(planned):
        for b in planned[i + 1:]:
            if a["group"] == b["group"]:
                pairs["same_brief" if a["brief_id"] == b["brief_id"] else "same_group"].append((a["shape"], b["shape"]))
    avg = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
    out = {k: {"pairs": len(v), "components_only": avg([sameness(a, b, False) for a, b in v]),
               "with_variants_and_direction": avg([sameness(a, b) for a, b in v])} for k, v in pairs.items()}
    out["direction"] = direction_report(planned)
    return out


def direction_report(planned: list[dict]) -> dict:
    """D-239: how alike the 8 varied direction choices are (the footer follows the page count, so it is left out),
    for different briefs in the same family and across families; random picking gives about 0.40."""
    from agents.planning.direction import FIELDS, family_of   # noqa: PLC0415
    avg = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
    match = lambda a, b: sum(a["direction"][f] == b["direction"][f] for f in FIELDS) / len(FIELDS)
    fam = {id(r): family_of(r.get("business_type")) for r in planned}
    same, cross = [], []
    for i, a in enumerate(planned):
        for b in planned[i + 1:]:
            if a["brief_id"] != b["brief_id"]:
                (same if fam[id(a)] == fam[id(b)] else cross).append(match(a["shape"], b["shape"]))
    spread = {f: max(Counter(r["shape"]["direction"][f] for r in planned).values()) / len(planned) for f in FIELDS}
    changes = Counter(c for r in planned for c in r["shape"].get("changes", []))
    return {"same_family": avg(same), "cross_family": avg(cross), "all_pairs": avg(same + cross),
            "pairs": [len(same), len(cross)], "most_common_share": {f: round(v, 2) for f, v in spread.items()},
            "presets_used": len({r["shape"].get("preset") for r in planned}),
            "changes_per_plan": round(sum(changes.values()) / len(planned), 2) if planned else 0,
            "changed_choices": dict(changes)}


def summary(rows: list[dict]) -> dict:
    def stats(group: list[dict]) -> dict:
        n = len(group)
        planned = [r for r in group if r["expect"] == "planned"]
        must = sum(len(r["must_found"]) + len(r["must_missing"]) for r in planned)
        return {
            "runs": n,
            "correct_outcome": round(sum(r["correct"] for r in group) / n, 3),
            "valid_plan_rate": round(sum(r["outcome"] == "planned" for r in planned) / len(planned), 3) if planned else None,
            "must_coverage": round(sum(len(r["must_found"]) for r in planned) / must, 3) if must else None,
            "must_not_leaks": sum(len(r["must_not_leaked"]) for r in group),
            "avg_questions": round(sum(r["questions"] for r in group) / n, 2),
            "avg_calls": round(sum(r["calls"] for r in group) / n, 2),
            "avg_fix_rounds": round(sum(r["fix_rounds"] for r in group) / n, 2),
            "avg_cost_usd": round(sum(r["cost_usd"] for r in group) / n, 4),
            "avg_seconds": round(sum(r["seconds"] for r in group) / n, 1),
        }
    by_group = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)
    failed_checks = Counter(i.split(":", 1)[0] for r in rows for i in r["final_issues"])
    failed_nodes = Counter(r["failure"]["node"] for r in rows if r["failure"])
    return {"overall": stats(rows), "groups": {g: stats(rs) for g, rs in by_group.items()},
            "failed_checks": dict(failed_checks), "failed_nodes": dict(failed_nodes),
            "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 4), "sameness": sameness_report(rows),
            "variety": variety_report(rows)}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=3, help="runs per brief (default 3)")
    parser.add_argument("--only", default="", help="comma-separated brief ids")
    parser.add_argument("--parallel", type=int, default=3, help="runs at the same time (default 3)")
    args = parser.parse_args()

    briefs = load_briefs({b.strip() for b in args.only.split(",") if b.strip()} or None)
    saver = InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist()))
    graph = build_forge_graph().compile(checkpointer=saver)
    gate = asyncio.Semaphore(args.parallel)

    async def limited(brief, n):
        async with gate:
            return await run_one(graph, brief, n)

    print(f"Evaluating {len(briefs)} briefs x {args.runs} runs (tracing {'on' if tracing.enabled() else 'off'})")
    rows = await asyncio.gather(*(limited(b, n) for b in briefs for n in range(1, args.runs + 1)))
    tracing.flush()

    result = {"at": datetime.now(timezone.utc).isoformat(), "runs_per_brief": args.runs,
              "models": _run_config().model_per_task, "rows": list(rows)}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"eval_{provider()}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")   # save rows before the summary can fail
    result["summary"] = summary(list(rows))
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSUMMARY")
    print(json.dumps(result["summary"], indent=2))
    print("Saved to:", out)


if __name__ == "__main__":
    asyncio.run(main())
