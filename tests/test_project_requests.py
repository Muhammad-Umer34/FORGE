"""
Integration tests: website requests belong to projects (D-179, D-180), on a real PostgreSQL database.
The agent graph is replaced by a small stand-in, so these tests check ownership, records and clean-up
without any model calls. Skipped unless TEST_DATABASE_URL is set.
"""
import asyncio
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, Header
from sqlalchemy import text

from backend.core.deps import get_current_user_id
from backend.db.session import get_session
from backend.routes.projects import router as projects_router
from backend.routes.requests import router as requests_router
from pg_support import migrate_test_database, new_engine, requires_db, session_dependency

pytestmark = requires_db
QUESTION = {"type": "question", "id": "q1", "text": "What should visitors do?"}


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    migrate_test_database()


class FakeGraph:
    """Stands in for the compiled FORGE graph and its checkpointer."""

    def __init__(self):
        self.threads: dict[str, str] = {}   # thread id -> what the run produced
        self.inputs: dict[str, object] = {}
        self.calls: list[str] = []
        self.deleted: list[str] = []
        self.next_outcome = "question"
        self.during_run = None             # optional coroutine factory run inside ainvoke
        self.checkpointer = self

    async def ainvoke(self, graph_input, config):
        thread = config["configurable"]["thread_id"]
        self.calls.append(f"invoke:{thread}")
        self.inputs[thread] = graph_input
        if self.during_run:
            await self.during_run()
        self.threads[thread] = self.next_outcome

    async def aget_state(self, config):
        thread = config["configurable"]["thread_id"]
        self.calls.append(f"state:{thread}")
        outcome = self.threads.get(thread)
        if outcome is None:
            return SimpleNamespace(values={}, interrupts=())
        if outcome == "question":
            return SimpleNamespace(values={"run": True}, interrupts=(SimpleNamespace(value=QUESTION),))
        reply = SimpleNamespace(model_dump=lambda: {"kind": "greeting", "message": "Hello!"})
        return SimpleNamespace(values={"clarification": SimpleNamespace(status="replied", reply=reply)}, interrupts=())

    async def adelete_thread(self, thread_id):
        self.deleted.append(thread_id)
        self.threads.pop(thread_id, None)


class Harness:
    def __init__(self, engine, client, graph):
        self.engine, self.client, self.graph = engine, client, graph
        self.users: list[uuid.UUID] = []

    async def user_with_projects(self, count: int = 1) -> tuple[uuid.UUID, list[uuid.UUID]]:
        uid = uuid.uuid4()
        projects = [uuid.uuid4() for _ in range(count)]
        async with self.engine.begin() as conn:
            await conn.execute(text("INSERT INTO users (id, email, password_hash, display_name) "
                                    "VALUES (:id, :e, '!', 'Test')"), {"id": uid, "e": f"req-test-{uid}@example.com"})
            for i, pid in enumerate(projects):
                await conn.execute(text("INSERT INTO projects (id, owner_id, name) VALUES (:p, :o, :n)"),
                                   {"p": pid, "o": uid, "n": f"Project {i}"})
        self.users.append(uid)
        return uid, projects

    def call(self, method: str, uid: uuid.UUID | None, path: str, **kwargs):
        headers = {"x-test-user": str(uid)} if uid else {}
        return self.client.request(method, path, headers=headers, **kwargs)

    async def start(self, uid, pid, prompt: str = "A website for my bakery") -> httpx.Response:
        return await self.call("POST", uid, f"/api/projects/{pid}/requests", json={"prompt": prompt})

    async def rows(self, pid: uuid.UUID) -> list:
        async with self.engine.connect() as conn:
            return (await conn.execute(text("SELECT id, status FROM requests WHERE project_id = :p"), {"p": pid})).all()


@asynccontextmanager
async def harness():
    engine = new_engine()
    graph = FakeGraph()

    def test_user(x_test_user: uuid.UUID | None = Header(default=None)) -> uuid.UUID:
        if x_test_user is None:
            from fastapi import HTTPException
            raise HTTPException(401, "Please sign in.")
        return x_test_user

    app = FastAPI()
    app.include_router(projects_router)
    app.include_router(requests_router)
    app.state.forge_graph = graph
    app.dependency_overrides[get_session] = session_dependency(engine)
    app.dependency_overrides[get_current_user_id] = test_user
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        h = Harness(engine, client, graph)
        try:
            yield h
        finally:
            if h.users:
                async with engine.begin() as conn:
                    await conn.execute(text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": h.users})
            await engine.dispose()


def run(coro):
    return asyncio.run(coro)


def test_request_is_recorded_in_the_project_with_the_real_user():
    async def scenario():
        async with harness() as h:
            uid, (pid,) = await h.user_with_projects()
            response = await h.start(uid, pid)
            assert response.status_code == 200
            envelope = response.json()
            assert envelope["status"] == "needs_clarification"
            rid = envelope["request_id"]
            assert await h.rows(pid) == [(rid, "needs_clarification")]
            info = h.graph.inputs[rid]["request"]
            assert (info.user_id, info.project_id) == (str(uid), str(pid))

            listed = (await h.call("GET", uid, f"/api/projects/{pid}/requests")).json()
            assert [(r["id"], r["status"], r["prompt"]) for r in listed] == [(rid, "needs_clarification", "A website for my bakery")]
            again = await h.call("GET", uid, f"/api/projects/{pid}/requests/{rid}")
            assert again.status_code == 200 and again.json()["data"] == QUESTION
    run(scenario())


def test_nobody_else_can_see_or_continue_a_request():
    async def scenario():
        async with harness() as h:
            owner, (pid, other_pid) = await h.user_with_projects(2)
            stranger, (stranger_pid,) = await h.user_with_projects()
            rid = (await h.start(owner, pid)).json()["request_id"]
            h.graph.calls.clear()

            attempts = [
                ("GET", stranger, f"/api/projects/{pid}/requests/{rid}", {}),
                ("GET", stranger, f"/api/projects/{stranger_pid}/requests/{rid}", {}),
                ("GET", owner, f"/api/projects/{other_pid}/requests/{rid}", {}),  # right user, wrong project
                ("GET", stranger, f"/api/projects/{pid}/requests", {}),
                ("POST", stranger, f"/api/projects/{pid}/requests/{rid}/answer",
                 {"json": {"question_id": "q1", "kind": "you_decide"}}),
                ("POST", stranger, f"/api/projects/{pid}/requests/{rid}/confirmation", {"json": {"decision": "confirm"}}),
                ("POST", stranger, f"/api/projects/{pid}/requests/{rid}/image?kind=logo",
                 {"files": {"file": ("logo.png", b"not really an image", "image/png")}}),
                ("POST", stranger, f"/api/projects/{pid}/requests", {"json": {"prompt": "Mine now"}}),
            ]
            for method, uid, path, kwargs in attempts:
                response = await h.call(method, uid, path, **kwargs)
                assert response.status_code == 404, (method, path, response.status_code)
            assert h.graph.calls == []  # the agent graph was never touched
            assert await h.rows(pid) == [(rid, "needs_clarification")]
    run(scenario())


def test_signed_out_callers_are_refused():
    async def scenario():
        async with harness() as h:
            _, (pid,) = await h.user_with_projects()
            assert (await h.call("GET", None, f"/api/projects/{pid}/requests")).status_code == 401
            assert (await h.call("POST", None, f"/api/projects/{pid}/requests", json={"prompt": "x"})).status_code == 401
            assert (await h.call("GET", None, f"/api/projects/{pid}/requests/req_000000000000")).status_code == 401
            assert h.graph.calls == []
    run(scenario())


def test_a_greeting_is_answered_but_not_kept():
    async def scenario():
        async with harness() as h:
            uid, (pid,) = await h.user_with_projects()
            h.graph.next_outcome = "reply"
            response = await h.start(uid, pid, "hello")
            assert response.json()["status"] == "reply"
            rid = response.json()["request_id"]
            assert await h.rows(pid) == []
            assert h.graph.deleted == [rid]
    run(scenario())


def test_deleting_a_project_deletes_its_requests_and_paused_runs():
    async def scenario():
        async with harness() as h:
            uid, (pid, keep_pid) = await h.user_with_projects(2)
            first = (await h.start(uid, pid)).json()["request_id"]
            second = (await h.start(uid, pid)).json()["request_id"]
            kept = (await h.start(uid, keep_pid)).json()["request_id"]

            assert (await h.call("DELETE", uid, f"/api/projects/{pid}")).status_code == 204
            assert await h.rows(pid) == []
            assert sorted(h.graph.deleted) == sorted([first, second])
            assert kept in h.graph.threads and await h.rows(keep_pid) == [(kept, "needs_clarification")]
            assert (await h.call("GET", uid, f"/api/projects/{pid}/requests/{first}")).status_code == 404
    run(scenario())


def test_project_deleted_while_the_agent_runs():
    async def scenario():
        async with harness() as h:
            uid, (pid,) = await h.user_with_projects()

            async def delete_project_meanwhile():
                async with h.engine.begin() as conn:
                    await conn.execute(text("DELETE FROM projects WHERE id = :p"), {"p": pid})

            h.graph.during_run = delete_project_meanwhile
            response = await h.start(uid, pid)
            assert response.status_code == 404
            assert len(h.graph.deleted) == 1  # the orphaned run was removed
            assert h.graph.threads == {}
    run(scenario())


def test_main_app_registers_projects_and_request_routes():
    from backend.main import app
    paths = app.openapi()["paths"]
    assert "/api/projects" in paths and "/api/projects/{project_id}/requests/{request_id}/answer" in paths
    assert not any(p.startswith("/api/requests") for p in paths)  # the old anonymous routes are gone
