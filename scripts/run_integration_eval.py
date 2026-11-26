# D:\FYP\FORGE-1\scripts\run_integration_eval.py
"""
Integration evaluation (D-252 - D-254, Integration Agent plan §8): when FORGE builds a site, do its parts fit, and
does a visitor's form really reach the site's database through the site itself?

    python scripts/run_integration_eval.py                 # all 12 data briefs
    python scripts/run_integration_eval.py --only d-salon,d-bakery

Each request is clarified and planned with the strict simulated owner (as the data evaluation does), then the real
build step runs: database on (storage on TEST_DATABASE_URL, for a throwaway project), live preview on, build gate off
(it has its own scoreboard). FORGE's site-data API runs on a local port against the same database, so the preview's
own routes reach it. Recorded per site: the integration checks, the live check, and the time of each branch (data,
frontend) against the build's wall time, which is the measured gain of running them side by side (FR-05).
Builds run one at a time (one live preview at a time). Real Gemini calls are made for planning.
Results: scripts/runs/integration_eval_<time>.json.
"""
import argparse
import asyncio
import json
import socket
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import psycopg  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer  # noqa: E402
from langgraph.types import Command  # noqa: E402

import run_data_eval as rde  # noqa: E402
from agents import file_store, preview  # noqa: E402
from agents.database_generator import agent as database_agent, provision  # noqa: E402
from agents.orchestrator import build_forge_graph  # noqa: E402
from agents.state import msgpack_allowlist  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.db.session import get_session  # noqa: E402
from backend.routes import site_data as site_routes  # noqa: E402
from backend.services import site_data  # noqa: E402
from pg_support import migrate_test_database, new_engine, session_dependency  # noqa: E402

BRIEFS = ROOT / "scripts" / "data_briefs.json"
OUT = ROOT / "scripts" / "runs"


def forge_api(url: str) -> uvicorn.Server:
    """FORGE's site-data routes on a free local port, reading keys from the test database."""
    app = FastAPI()
    app.include_router(site_routes.router)
    app.dependency_overrides[get_session] = session_dependency(new_engine())
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                                           loop="asyncio:SelectorEventLoop"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    settings.FORGE_API_URL = f"http://127.0.0.1:{port}"
    return server


def throwaway_project(url: str, brief_id: str) -> tuple[str, str]:
    with psycopg.connect(url, autocommit=True) as conn:
        user = conn.execute("INSERT INTO users (email, password_hash, display_name) VALUES (%s, 'x', 'Eval') "
                            "RETURNING id", (f"ieval-{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]
        project = conn.execute("INSERT INTO projects (owner_id, name) VALUES (%s, %s) RETURNING id",
                               (user, f"ieval {brief_id}")).fetchone()[0]
    return str(user), str(project)


def remove_project(url: str, user: str, project: str) -> None:
    provision.drop(url, project)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))


async def build_one(graph, brief: dict, url: str) -> dict:
    user, project = throwaway_project(url, brief["id"])
    request_id = f"ieval_{brief['id']}_{uuid.uuid4().hex[:6]}"
    row = {"id": brief["id"], "family": brief["family"]}
    try:
        values, seconds, error = await rde.plan_one(graph, brief, project,
                                                    {"preview": True, "database": True, "build_gate": False},
                                                    request_id)
        p = values.get("planning")
        row.update(plan_seconds=round(seconds, 1), planned=bool(values.get("plan") and p
                                                               and p.status == "awaiting_approval" and not error))
        if not row["planned"]:
            row["error"] = error or (p.failure.detail[:300] if p and p.failure else "not planned")
            return row
        config = {"configurable": {"thread_id": request_id}}
        first, last, started = {}, {}, time.perf_counter()
        lines = []
        async for event in graph.astream(Command(resume={"decision": "approve", "change_text": None}), config,
                                         stream_mode="custom"):
            now = time.perf_counter() - started
            branch = {"database": "data", "backend": "data"}.get(event.get("agent"), event.get("agent") or "frontend")
            first.setdefault(branch, now)
            last[branch] = now
            if event.get("message"):
                lines.append(event["message"])
        wall = time.perf_counter() - started
        state = (await graph.aget_state(config)).values
        arts = state.get("artifacts") or {}
        stored = file_store.active_store().read(request_id)
        summary = json.loads(stored.get("forge/integration.json") or "{}")
        live = summary.get("live")
        data_s = last.get("data", 0) - first.get("data", 0)
        front_s = last.get("frontend", 0) - first.get("frontend", 0)
        row.update({
            "statuses": {a: arts[a].status for a in arts},
            "checks_passed": summary.get("passed", 0), "checks": summary.get("total", 0),
            "failed_checks": [c["message"] for c in summary.get("checks", []) if not c["ok"]],
            "live": None if live is None else all(s["ok"] for s in live),
            "live_steps": live, "ready": "Your site is ready" in lines,
            "build_seconds": round(wall, 1), "data_seconds": round(data_s, 1), "frontend_seconds": round(front_s, 1),
            "one_after_another_seconds": round(data_s + front_s, 1),
            "problems": [m for m in lines if "failed" in m.lower() or "bug" in m.lower()][:5],
            "lines": lines,
        })
    except Exception as e:                                   # a crash is a result too
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        preview.stop_all()
        remove_project(url, user, project)
    return row


def summary(rows: list[dict]) -> dict:
    built = [r for r in rows if r.get("checks")]
    lived = [r for r in built if r.get("live") is not None]
    return {
        "requests": len(rows), "planned": sum(bool(r.get("planned")) for r in rows), "built": len(built),
        "all_checks_passed": f"{sum(r['checks_passed'] == r['checks'] for r in built)}/{len(built)}",
        "checks": f"{sum(r['checks_passed'] for r in built)}/{sum(r['checks'] for r in built)}",
        "live_passed": f"{sum(bool(r['live']) for r in lived)}/{len(lived)}",
        "ready": f"{sum(r['ready'] for r in built)}/{len(built)}",
        "avg_build_seconds": round(sum(r["build_seconds"] for r in built) / max(1, len(built)), 1),
        "avg_one_after_another_seconds": round(sum(r["one_after_another_seconds"] for r in built) / max(1, len(built)), 1),
        "not_built": [r["id"] for r in rows if not r.get("checks")],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--only", default="", help="comma-separated request ids")
    args = parser.parse_args()
    if not settings.TEST_DATABASE_URL:
        raise SystemExit("TEST_DATABASE_URL is not set: the evaluation builds on the test database")
    url = provision.plain_url(settings.TEST_DATABASE_URL)
    settings.SITE_DB_URL = url                               # site storage and the key registry: the test database
    database_agent.app_url = lambda: url
    site_data.use_pool(None)
    site_data.pool(url)
    server = forge_api(url)
    wanted = {i.strip() for i in args.only.split(",") if i.strip()}
    briefs = [b for b in json.loads(BRIEFS.read_text(encoding="utf-8"))["briefs"] if not wanted or b["id"] in wanted]
    graph = build_forge_graph().compile(
        checkpointer=InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist())))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"integration_eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    rows = []
    for brief in briefs:                                     # one live preview at a time
        row = await build_one(graph, brief, url)
        rows.append(row)
        print(f"  {row['id']}: " + (f"checks {row['checks_passed']}/{row['checks']}, live {row['live']}, "
                                    f"ready {row['ready']}, build {row['build_seconds']} s (data {row['data_seconds']} "
                                    f"+ frontend {row['frontend_seconds']} s one after another)"
                                    if row.get("checks") else f"NOT BUILT ({row.get('error')})"), flush=True)
        out.write_text(json.dumps({"rows": rows}, indent=2, default=str), encoding="utf-8")
    result = {"at": datetime.now(timezone.utc).isoformat(), "rows": rows, "summary": summary(rows)}
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    server.should_exit = True
    print("\nSUMMARY\n" + json.dumps(result["summary"], indent=2) + f"\nSaved to: {out}")


if __name__ == "__main__":
    migrate_test_database()                                  # alembic runs its own event loop: before ours
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
