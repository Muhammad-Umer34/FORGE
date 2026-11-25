# D:\FYP\FORGE-1\scripts\run_data_eval.py
"""
Data evaluation (D-242 - D-245, Database Agent plan §10): does FORGE turn a request into the data the business needs,
keep the owner's answers, and build storage whose every rule holds?

    python scripts/run_data_eval.py                 # all 12 requests, 3 at a time
    python scripts/run_data_eval.py --only d-salon,d-yoga

Each request goes through clarification and planning with the strict simulated owner (scripts/run_eval.py), stopping
at the plan screen (no build). Its data is then compiled and proved by the database gate on TEST_DATABASE_URL (a
scratch schema, rolled back). Then the backend stage (D-247, D2): the storage is made for a throwaway project, and
FORGE's real site-data routes are called with its key: each form's sample submission must be saved, a wrong key
refused (401), and one rule-breaking submission refused with the right code (a repeat for a table with a no-overlap
or once-only rule, 409; otherwise a missing required field, 422). Real Gemini calls are made. Results:
scripts/runs/data_eval_<time>.json.
"""
import argparse
import asyncio
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer  # noqa: E402
from langgraph.types import Command  # noqa: E402

import run_eval as ev  # noqa: E402
from agents.database_generator.gate import run_gate  # noqa: E402
from agents.backend_generator.agent import form_specs  # noqa: E402
from agents.backend_generator.gate import sample_payload  # noqa: E402
from agents.database_generator import provision  # noqa: E402
from agents.database_generator.provision import plain_url  # noqa: E402
from agents.database_generator.seed import seed_rows  # noqa: E402
from agents.orchestrator import build_forge_graph  # noqa: E402
from agents.state import RequestInfo, initial_state, msgpack_allowlist  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.routes.requests import _run_config  # noqa: E402

BRIEFS = ROOT / "scripts" / "data_briefs.json"
OUT = ROOT / "scripts" / "runs"


async def plan_one(graph, brief: dict) -> tuple[dict, float, str | None]:
    """Clarify and plan with the simulated owner; stop at the plan screen. Returns (state values, seconds, error)."""
    request_id = f"deval_{brief['id']}_{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": request_id}}
    run_config = _run_config().model_copy(update={"preview": False, "build_gate": False, "database": False})
    graph_input = initial_state(RequestInfo(request_id=request_id, user_id="eval", project_id="eval",
                                            prompt=brief["prompt"], created_at=datetime.now(timezone.utc)),
                                config=run_config)
    started, error, values = time.perf_counter(), None, {}
    try:
        for _ in range(ev.MAX_TURNS):
            await graph.ainvoke(graph_input, config)
            snapshot = await graph.aget_state(config)
            values = snapshot.values
            if snapshot.interrupts and snapshot.interrupts[0].value.get("type") == "plan_approval":
                # paused inside the planning subgraph: its plan is in the subgraph's state, not yet in the run's
                inner = await graph.aget_state(config, subgraphs=True)
                values = dict(values)
                for task in inner.tasks:
                    if task.state is not None:
                        values.update({k: v for k, v in task.state.values.items() if k in ("plan", "planning")})
                break
            if not snapshot.interrupts:
                break
            graph_input = Command(resume=ev.reply(snapshot.interrupts[0].value, brief["answers"]))
    except Exception as e:   # an outage is a result too
        error = f"{type(e).__name__}: {e}"[:300]
    return values, time.perf_counter() - started, error


def _names(plan) -> dict[str, str]:
    """Recipe entity name -> the name in this plan (renames followed)."""
    out = {}
    for r in plan.data_recipes:
        out.update(r.get("names") or {})
    return out


def _has_field(plan, spec: str, names: dict[str, str]) -> bool:
    if spec.startswith("*"):
        word = spec.strip("*")
        return any(word in f.name or word in (f.label or "").lower() for e in plan.data_entities for f in e.fields)
    entity, _, field = spec.partition(".")
    e = next((x for x in plan.data_entities if x.name == names.get(entity, entity)), None)
    return bool(e and any(f.name == field for f in e.fields))


def _has_rule(plan, spec: str, names: dict[str, str]) -> bool:
    entity, _, kind = spec.partition(".")
    e = next((x for x in plan.data_entities if x.name == names.get(entity, entity)), None)
    return bool(e and any(r.kind == kind and r.enabled for r in e.rules))


def measure(brief: dict, values: dict, seconds: float, error: str | None) -> dict:
    plan, p, c, usage = values.get("plan"), values.get("planning"), values.get("clarification"), values.get("usage")
    planned = bool(plan and p and p.status == "awaiting_approval" and not error)
    row = {"id": brief["id"], "family": brief["family"], "planned": planned, "error": error,
           "seconds": round(seconds, 1), "cost_usd": round(usage.estimated_cost_usd, 4) if usage else 0.0,
           "data_questions": [q.text for q in (c.questions if c else []) if q.kind == "F"],
           "failure": (p.failure.detail[:300] if p and p.failure else None)}
    if not planned:
        if not row["failure"] and not error:
            row["error"] = f"stopped with planning '{p.status if p else None}' and no plan"
        return row
    names = _names(plan)
    used = [r["pattern"] for r in plan.data_recipes]
    want = brief["expect_recipes"]
    recipes_ok = (any(r in used for r in want) if brief.get("expect_any_recipe") else all(r in used for r in want))
    switches = {f"{r['pattern']}.{k}": v for r in plan.data_recipes for k, v in (r.get("switches") or {}).items()}
    kept = {k: switches.get(k) == v for k, v in brief["expect_switches"].items()}
    owner = brief["answers"].get("data", {})
    owner_kept = {k: switches.get(k) == v for k, v in owner.items() if k.split(".")[0] in used}
    fields = {s: _has_field(plan, s, names) for s in brief["must_fields"]}
    rules = {s: _has_rule(plan, s, names) for s in brief["must_rules"]}
    must = list(fields.values()) + list(rules.values())
    gate_started = time.perf_counter()
    result, _ = run_gate(plan.data_entities, plain_url(settings.TEST_DATABASE_URL), f"deval-{brief['id']}")
    row.update({
        "recipes": used, "renames": names, "custom": [e.name for e in plan.data_entities if e.pattern == "custom"],
        "extra_fields": sorted({f.name for e in plan.data_entities for f in e.fields} - _recipe_fields(plan)),
        "recipes_ok": recipes_ok, "switches_kept": kept, "owner_answers_kept": owner_kept,
        "must_fields": fields, "must_rules": rules, "must_coverage": round(sum(must) / len(must), 3) if must else 1.0,
        "tables": len(plan.data_entities), "rules": sum(1 for e in plan.data_entities for r in e.rules if r.enabled),
        "gate_ok": result.ok, "rule_tests": len(result.tests), "rule_tests_passed": result.passed,
        "gate_message": result.message, "gate_seconds": round(time.perf_counter() - gate_started, 1),
        "data_problems": list(plan.data_problems), "fix_rounds": p.fix_rounds_used,
    })
    if result.ok:
        row["backend"] = backend_stage(plan, brief["id"])
    return row


REPEAT_REFUSED = {"no_overlap", "unique_together"}


def backend_stage(plan, brief_id: str) -> dict:
    """Real HTTP calls to FORGE's site-data routes (in process) on storage made for a throwaway project."""
    import httpx
    import psycopg
    from fastapi import FastAPI

    from backend.db.session import get_session
    from backend.routes import site_data as routes
    from backend.services import site_data
    sys.path.insert(0, str(ROOT / "tests"))
    from pg_support import new_engine, session_dependency

    url = plain_url(settings.TEST_DATABASE_URL)
    specs = {s["table"]: s for s in form_specs(plan).values()}
    out = {"forms": len(specs), "checks": [], "error": None}
    with psycopg.connect(url, autocommit=True) as conn:
        user = conn.execute("INSERT INTO users (email, password_hash, display_name) VALUES (%s, 'x', 'Eval') "
                            "RETURNING id", (f"deval-{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]
        project = str(conn.execute("INSERT INTO projects (owner_id, name) VALUES (%s, %s) RETURNING id",
                                   (user, f"deval {brief_id}")).fetchone()[0])
    site_data.use_pool(None)
    site_data.pool(url)
    routes._hits.clear()
    try:
        made = provision.provision(plan.data_entities, url, project)
        key = provision.register(url, project, made, f"deval_{brief_id}")
        rows = seed_rows(plan.data_entities, made["contract"].get("time_zone") or "Asia/Karachi")
        by_name = {e.name: e for e in plan.data_entities}

        async def calls():
            engine = new_engine()
            app = FastAPI()
            app.include_router(routes.router)
            app.dependency_overrides[get_session] = session_dependency(engine)
            checks = []
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://forge") as client:
                async def post(table, body, k=key):
                    r = await client.post(f"/api/site-data/{table}", json=body, headers={"X-Forge-Site-Key": k})
                    return r.status_code, (r.json().get("message") or "")

                for table, spec in specs.items():
                    payload = sample_payload(spec, rows, plan)
                    code, message = await post(table, payload)
                    saved = code == 201
                    checks.append({"table": table, "check": "sample saved", "ok": saved, "got": f"{code} {message}"[:200]})
                    code, _ = await post(table, payload, "fsk_wrong")
                    checks.append({"table": table, "check": "wrong key refused", "ok": code == 401, "got": str(code)})
                    kinds = {r.kind for r in by_name[table].rules if r.enabled} & REPEAT_REFUSED
                    if kinds:
                        code, message = await post(table, payload)
                        checks.append({"table": table, "check": f"repeat refused ({sorted(kinds)[0]})",
                                       "ok": saved and code == 409, "got": f"{code} {message}"[:200]})
                        continue           # a refused first save makes the repeat's 409 meaningless, so it fails too
                    required = next((f["name"] for f in spec["fields"] if f["required"] and f["name"] in payload), None)
                    if required:
                        code, message = await post(table, {k: v for k, v in payload.items() if k != required})
                        checks.append({"table": table, "check": f"missing '{required}' refused", "ok": code == 422,
                                       "got": f"{code} {message}"[:200]})
            await engine.dispose()
            return checks

        out["checks"] = asyncio.run(calls(), loop_factory=asyncio.SelectorEventLoop)
    except Exception as e:      # a crash here is a result too
        out["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        provision.drop(url, project)
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("DELETE FROM users WHERE id = %s", (user,))
        site_data.pool().close()
        site_data.use_pool(None)
    out["passed"] = sum(c["ok"] for c in out["checks"])
    out["ok"] = not out["error"] and out["forms"] > 0 and out["passed"] == len(out["checks"])
    return out


def _recipe_fields(plan) -> set[str]:
    from agents.planning import data_patterns as dp
    out = set()
    for r in plan.data_recipes:
        entities, _ = dp.expand([r])
        out |= {f.name for e in entities for f in e.fields}
    return out


def summary(rows: list[dict]) -> dict:
    planned = [r for r in rows if r["planned"]]
    owner = [v for r in planned for v in r["owner_answers_kept"].values()]
    return {
        "requests": len(rows), "planned": len(planned),
        "recipes_right": sum(r["recipes_ok"] for r in planned),
        "schema_applies_and_rules_hold": sum(r["gate_ok"] for r in planned),
        "rule_tests": sum(r["rule_tests"] for r in planned), "rule_tests_passed": sum(r["rule_tests_passed"] for r in planned),
        "owner_answers_kept": f"{sum(owner)}/{len(owner)}",
        "must_coverage": round(sum(r["must_coverage"] for r in planned) / max(1, len(planned)), 3),
        "avg_tables": round(sum(r["tables"] for r in planned) / max(1, len(planned)), 1),
        "avg_rules": round(sum(r["rules"] for r in planned) / max(1, len(planned)), 1),
        "avg_seconds": round(sum(r["seconds"] for r in rows) / max(1, len(rows)), 1),
        "avg_gate_seconds": round(sum(r["gate_seconds"] for r in planned) / max(1, len(planned)), 2),
        "avg_cost_usd": round(sum(r["cost_usd"] for r in rows) / max(1, len(rows)), 4),
        "custom_record_types": sum(len(r["custom"]) for r in planned),
        "backend_sites_ok": f"{sum(bool(r.get('backend', {}).get('ok')) for r in planned)}/{len(planned)}",
        "backend_checks": f"{sum(r.get('backend', {}).get('passed', 0) for r in planned)}"
                          f"/{sum(len(r.get('backend', {}).get('checks', [])) for r in planned)}",
        "backend_forms": sum(r.get("backend", {}).get("forms", 0) for r in planned),
        "not_planned": [r["id"] for r in rows if not r["planned"]],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--only", default="", help="comma-separated request ids")
    parser.add_argument("--parallel", type=int, default=3)
    parser.add_argument("--gap", type=float, default=0, help="seconds to wait between requests (per-minute quotas)")
    args = parser.parse_args()
    if not settings.TEST_DATABASE_URL:
        raise SystemExit("TEST_DATABASE_URL is not set: the gate needs a test database")
    wanted = {i.strip() for i in args.only.split(",") if i.strip()}
    briefs = [b for b in json.loads(BRIEFS.read_text(encoding="utf-8"))["briefs"] if not wanted or b["id"] in wanted]
    graph = build_forge_graph().compile(
        checkpointer=InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist())))
    gate = asyncio.Semaphore(args.parallel)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"data_eval_{datetime.now():%Y%m%d_%H%M%S}.json"

    async def one(brief):
        async with gate:
            values, seconds, error = await plan_one(graph, brief)
            await asyncio.sleep(args.gap)
        row = await asyncio.to_thread(measure, brief, values, seconds, error)
        print(f"  {row['id']}: {'planned' if row['planned'] else 'NOT PLANNED'}"
              + (f", recipes {row['recipes']}, {row['tables']} tables, {row['rules']} rules, gate "
                 f"{row['rule_tests_passed']}/{row['rule_tests']}, coverage {row['must_coverage']}"
                 + (f", backend {row['backend']['passed']}/{len(row['backend']['checks'])}"
                    + (f" ({row['backend']['error']})" if row["backend"]["error"] else "") if "backend" in row else "")
                 if row["planned"] else
                 f" ({row['error'] or row['failure']})"), flush=True)
        return row

    rows = await asyncio.gather(*(one(b) for b in briefs))
    result = {"at": datetime.now(timezone.utc).isoformat(), "rows": list(rows)}
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    result["summary"] = summary(list(rows))
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("\nSUMMARY\n" + json.dumps(result["summary"], indent=2) + f"\nSaved to: {out}")


if __name__ == "__main__":
    asyncio.run(main())
