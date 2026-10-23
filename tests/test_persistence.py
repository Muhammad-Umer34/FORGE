"""
Persistence and resume (persistence plan). A small real LangGraph graph built like FORGE's: an agent subgraph
(step_a -> step_b) followed by a finishing step, run through the real request API on the test database.
Every step counts its runs, so the tests can show that finished steps never run again after a resume.
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sqlalchemy import text

from agents.gateway import ModelCallError
from agents.state import ClarificationState, GraphState, RequestInfo, initial_state, msgpack_allowlist
from backend.core.config import settings
from backend.db.checkpoints import open_checkpointer
from backend.db.session import make_sessionmaker
from backend.routes import requests as routes
from pg_support import migrate_test_database, requires_db
from test_limits import app_harness, verified_user_with_project


def run(coro):
    return asyncio.run(coro)


class Flaky:
    """Graph parts whose steps count their runs; step_b fails `failures` times like an unreachable model."""

    def __init__(self, failures=1, ask_user=False, slow=0.0):
        self.runs = {"step_a": 0, "step_b": 0, "finish": 0}
        self.failures, self.ask_user, self.slow = failures, ask_user, slow

    async def step_a(self, state):
        self.runs["step_a"] += 1
        return {"errors": []}

    async def step_b(self, state):
        self.runs["step_b"] += 1
        if self.slow:
            await asyncio.sleep(self.slow)
        if self.failures:
            self.failures -= 1
            raise ModelCallError("503 UNAVAILABLE")
        if self.ask_user:
            interrupt({"type": "question", "question_id": "q1", "text": "Who is the site for?"})
        return {"errors": []}

    async def finish(self, state):
        self.runs["finish"] += 1
        return {"clarification": ClarificationState(status="cancelled")}

    def build(self, checkpointer=None):
        agent = StateGraph(GraphState)
        agent.add_node("step_a", self.step_a)
        agent.add_node("step_b", self.step_b)
        agent.add_edge(START, "step_a")
        agent.add_edge("step_a", "step_b")
        agent.add_edge("step_b", END)
        main = StateGraph(GraphState)
        main.add_node("agent", agent.compile())          # inherits the checkpointer, like FORGE's agents
        main.add_node("finish", self.finish)
        main.add_edge(START, "agent")
        main.add_edge("agent", "finish")
        main.add_edge("finish", END)
        saver = checkpointer or InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist()))
        return main.compile(checkpointer=saver)


@pytest.fixture(scope="module")
def migrated():
    migrate_test_database()


async def stored_status(h, request_id):
    async with h.engine.connect() as conn:
        return await conn.scalar(text("SELECT status FROM requests WHERE id = :r"), {"r": request_id})


async def start(h, flaky):
    pid, _ = await verified_user_with_project(h)
    async with h.engine.begin() as conn:   # one website per project: start from an empty project
        await conn.execute(text("DELETE FROM requests WHERE project_id = :p"), {"p": pid})
    response = await h.client.post(f"/api/projects/{pid}/requests", json={"prompt": "A bakery website"})
    return pid, response


@requires_db
def test_a_stopped_run_pauses_and_continues_without_redoing_finished_steps(migrated):
    flaky = Flaky(failures=1)

    async def scenario():
        async with app_harness(flaky.build()) as h:
            pid, first = await start(h, flaky)
            body = first.json()
            rid = body["request_id"]
            assert first.status_code == 200 and body["status"] == "paused"
            assert await stored_status(h, rid) == "paused"
            assert (await h.client.get(f"/api/projects/{pid}/requests/{rid}")).json()["status"] == "paused"
            assert flaky.runs == {"step_a": 1, "step_b": 1, "finish": 0}

            resumed = await h.client.post(f"/api/projects/{pid}/requests/{rid}/resume")
            assert resumed.status_code == 200 and resumed.json()["status"] == "cancelled"   # reached the end
            assert flaky.runs == {"step_a": 1, "step_b": 2, "finish": 1}     # only the failed step ran again
            assert await stored_status(h, rid) == "cancelled"

            again = await h.client.post(f"/api/projects/{pid}/requests/{rid}/resume")
            assert again.status_code == 409 and "finished" in again.json()["detail"]
    run(scenario())


@requires_db
def test_cancelling_a_paused_run_deletes_what_was_saved(migrated):
    flaky = Flaky(failures=1)
    graph = flaky.build()

    async def scenario():
        async with app_harness(graph) as h:
            pid, first = await start(h, flaky)
            rid = first.json()["request_id"]
            cancelled = await h.client.post(f"/api/projects/{pid}/requests/{rid}/cancel")
            assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
            assert not (await graph.aget_state({"configurable": {"thread_id": rid}})).values
            assert (await h.client.get(f"/api/projects/{pid}/requests/{rid}")).json()["status"] == "cancelled"
            assert (await h.client.post(f"/api/projects/{pid}/requests/{rid}/resume")).status_code == 409
    run(scenario())


@requires_db
def test_two_continues_at_once_run_the_step_only_once(migrated):
    flaky = Flaky(failures=1, slow=0.4)

    async def scenario():
        async with app_harness(flaky.build()) as h:
            pid, first = await start(h, flaky)
            rid = first.json()["request_id"]
            url = f"/api/projects/{pid}/requests/{rid}/resume"
            a, b = await asyncio.gather(h.client.post(url), h.client.post(url))
            assert sorted([a.status_code, b.status_code]) == [200, 409]
            assert flaky.runs["step_b"] == 2 and flaky.runs["finish"] == 1
    run(scenario())


@requires_db
def test_waiting_for_the_user_survives_a_restart(migrated):
    flaky = Flaky(failures=0, ask_user=True)
    saver = InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist()))

    async def scenario():
        async with app_harness(flaky.build(saver)) as h:
            pid, first = await start(h, flaky)
            rid = first.json()["request_id"]
            assert first.json()["status"] == "needs_clarification"
            h.app.state.forge_graph = flaky.build(saver)        # a "restarted" server: new graph, same saved runs
            shown = (await h.client.get(f"/api/projects/{pid}/requests/{rid}")).json()
            assert shown["status"] == "needs_clarification" and shown["data"]["question_id"] == "q1"
            assert flaky.runs == {"step_a": 1, "step_b": 1, "finish": 0}  # reading the screen ran nothing
    run(scenario())


@requires_db
def test_startup_repair_and_lost_checkpoints(migrated):
    flaky = Flaky(failures=1)
    graph = flaky.build()

    async def scenario():
        async with app_harness(graph) as h:
            pid, first = await start(h, flaky)
            rid = first.json()["request_id"]
            async with h.engine.begin() as conn:      # as if the server had crashed during the run
                await conn.execute(text("UPDATE requests SET status = 'processing' WHERE id = :r"), {"r": rid})
            async with make_sessionmaker(h.engine)() as session:
                await routes.repair_statuses(graph, session)
            assert await stored_status(h, rid) == "paused"

            await graph.checkpointer.adelete_thread(rid)  # the saved run is gone
            gone = (await h.client.get(f"/api/projects/{pid}/requests/{rid}")).json()
            assert gone["status"] == "failed" and "no longer be continued" in gone["data"]["message"]
            assert await stored_status(h, rid) == "failed"
    run(scenario())


@requires_db
def test_resume_checks_the_code_version_and_the_limit(migrated, monkeypatch):
    flaky = Flaky(failures=3)

    async def scenario():
        async with app_harness(flaky.build()) as h:
            pid, first = await start(h, flaky)
            rid = first.json()["request_id"]
            url = f"/api/projects/{pid}/requests/{rid}/resume"
            monkeypatch.setattr(settings, "LIMIT_RESUMES_PER_REQUEST_HOUR", 1)
            assert (await h.client.post(url)).json()["status"] == "paused"     # failed again: still paused
            assert (await h.client.post(url)).status_code == 429               # limit per request per hour
            monkeypatch.setattr(settings, "LIMIT_RESUMES_PER_REQUEST_HOUR", 1_000_000)
            monkeypatch.setattr(routes, "STATE_VERSION", 99)                   # FORGE was updated meanwhile
            updated = (await h.client.post(url)).json()
            assert updated["status"] == "failed" and "updated" in updated["data"]["message"]
    run(scenario())


@requires_db
def test_runs_saved_in_postgres_survive_reopening_the_saver(migrated):
    flaky = Flaky(failures=0, ask_user=True)
    rid = f"req_test_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": rid}}

    async def scenario():
        async with open_checkpointer(settings.TEST_DATABASE_URL) as saver:
            graph = flaky.build(saver)
            state = initial_state(RequestInfo(request_id=rid, user_id="t", project_id="t", prompt="x",
                                              created_at=datetime.now(timezone.utc)))
            await graph.ainvoke(state, config, durability="sync")
        async with open_checkpointer(settings.TEST_DATABASE_URL) as saver:     # a new server process
            snapshot = await flaky.build(saver).aget_state(config)
            assert snapshot.interrupts and snapshot.interrupts[0].value["question_id"] == "q1"
            await saver.adelete_thread(rid)
            assert not (await flaky.build(saver).aget_state(config)).values

    asyncio.run(scenario(), loop_factory=asyncio.SelectorEventLoop)   # psycopg needs it on Windows


@requires_db
def test_one_website_per_project_and_start_over(migrated, monkeypatch):
    flaky = Flaky(failures=0, ask_user=True)
    monkeypatch.setattr(settings, "LIMIT_REQUESTS_PER_USER_DAY", 2)

    async def scenario():
        async with app_harness(flaky.build()) as h:
            pid, _ = await verified_user_with_project(h)
            async with h.engine.begin() as conn:   # start with an empty project (the helper adds a request row)
                await conn.execute(text("DELETE FROM requests WHERE project_id = :p"), {"p": pid})
            url = f"/api/projects/{pid}/requests"
            first = (await h.client.post(url, json={"prompt": "A salon website"})).json()
            assert first["status"] == "needs_clarification"

            second = await h.client.post(url, json={"prompt": "A bakery website"})
            assert second.status_code == 409 and second.json()["detail"]["code"] == "website_in_progress"

            cancelled = await h.client.post(f"{url}/{first['request_id']}/cancel")   # Start over
            flaky.ask_user = False                   # the next run goes straight to its end
            assert cancelled.json()["status"] == "cancelled"
            again = await h.client.post(url, json={"prompt": "A bakery website"})
            assert again.status_code == 200          # not 429: the refused request did not use the daily limit

            done = again.json()["request_id"]
            async with h.engine.begin() as conn:     # as if it had ended with a finished brief
                await conn.execute(text("UPDATE requests SET status = 'complete' WHERE id = :r"), {"r": done})
            assert (await h.client.post(f"{url}/{done}/cancel")).json()["status"] == "cancelled"
            assert (await h.client.post(f"{url}/{done}/cancel")).status_code == 409   # nothing left to cancel
    run(scenario())
