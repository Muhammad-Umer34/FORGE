"""
Integration tests for the 3-projects-per-user limit (D-174, D-175) on a real PostgreSQL database.
Skipped unless TEST_DATABASE_URL is set in .env. Each test creates its own users and deletes them
(and, by cascade, their projects) at the end, so the tests never touch other data.

To make "at the same time" certain rather than lucky, most tests first hold the user's row lock
from a separate connection, start the requests, wait until PostgreSQL shows them all waiting on
that lock, and only then release it. At that moment every request has passed every check that
comes before the lock - exactly the situation a race condition needs.
"""
import asyncio
import importlib.util
import time
import uuid
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI, Header
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from backend.core.deps import get_current_user_id, get_verified_user_id
from backend.db.session import get_session, sqlstate
from backend.routes.projects import router as projects_router
from backend.services import projects as service
from pg_support import (MIGRATIONS, EmptyGraph, migrate_test_database, new_engine, open_transactions, requires_db,
                        session_dependency, wait_for_lock_waiters)

pytestmark = requires_db


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    migrate_test_database()


@pytest.fixture(autouse=True)
def long_lock_timeout(monkeypatch):
    """Requests must outwait the test's own lock holder; one test lowers this again."""
    monkeypatch.setattr(service, "LOCK_TIMEOUT_MS", 20_000)


class Harness:
    def __init__(self, engine, client):
        self.engine = engine
        self.client = client
        self.users: list[uuid.UUID] = []

    async def new_user(self, projects: int = 0) -> uuid.UUID:
        uid = uuid.uuid4()
        async with self.engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO users (id, email, password_hash, display_name) VALUES (:id, :email, '!', 'Test')"),
                {"id": uid, "email": f"limit-test-{uid}@forge.test"},
            )
            for i in range(projects):
                await conn.execute(text("INSERT INTO projects (owner_id, name) VALUES (:o, :n)"), {"o": uid, "n": f"Seed {i}"})
        self.users.append(uid)
        return uid

    async def create(self, uid: uuid.UUID, name: str) -> httpx.Response:
        return await self.client.post("/api/projects", json={"name": name}, headers={"x-test-user": str(uid)})

    async def count(self, uid: uuid.UUID) -> int:
        async with self.engine.connect() as conn:
            return await conn.scalar(text("SELECT count(*) FROM projects WHERE owner_id = :o"), {"o": uid})

    @asynccontextmanager
    async def hold_user_lock(self, uid: uuid.UUID):
        """Hold the same row lock create_project takes, from a separate transaction."""
        async with self.engine.connect() as conn:
            trans = await conn.begin()
            await conn.execute(text("SELECT id FROM users WHERE id = :id FOR UPDATE"), {"id": uid})
            try:
                yield
            finally:
                await trans.rollback()

    async def wait_for_lock_waiters(self, count: int, statement: str = "FOR UPDATE") -> None:
        await wait_for_lock_waiters(self.engine, count, statement)

    async def open_transactions(self) -> int:
        return await open_transactions(self.engine, "projects")


@asynccontextmanager
async def harness():
    engine = new_engine()

    def test_user(x_test_user: uuid.UUID = Header()) -> uuid.UUID:
        return x_test_user

    app = FastAPI()
    app.include_router(projects_router)
    app.state.forge_graph = EmptyGraph()
    app.dependency_overrides[get_session] = session_dependency(engine)
    app.dependency_overrides[get_current_user_id] = test_user
    app.dependency_overrides[get_verified_user_id] = test_user
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        h = Harness(engine, client)
        try:
            yield h
        finally:
            if h.users:
                async with engine.begin() as conn:
                    await conn.execute(text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": h.users})
            await engine.dispose()


def run(coro):
    return asyncio.run(coro)


def codes(responses) -> list[int]:
    return sorted(r.status_code for r in responses)


# --- the five required concurrency cases --------------------------------------------------------

def test_user_with_two_projects_sends_two_at_once_exactly_one_succeeds():
    async def scenario():
        async with harness() as h:
            uid = await h.new_user(projects=2)
            async with h.hold_user_lock(uid):
                tasks = [asyncio.create_task(h.create(uid, f"Parallel {i}")) for i in range(2)]
                await h.wait_for_lock_waiters(2)
            responses = await asyncio.gather(*tasks)
            assert codes(responses) == [201, 409]
            rejected = next(r for r in responses if r.status_code == 409)
            assert rejected.json()["detail"]["code"] == "project_limit_reached"
            assert await h.count(uid) == 3
    run(scenario())


def test_user_with_three_projects_sends_several_at_once_none_succeeds():
    async def scenario():
        async with harness() as h:
            uid = await h.new_user(projects=3)
            async with h.hold_user_lock(uid):
                tasks = [asyncio.create_task(h.create(uid, f"Parallel {i}")) for i in range(3)]
                await h.wait_for_lock_waiters(3)
            responses = await asyncio.gather(*tasks)
            assert codes(responses) == [409, 409, 409]
            assert await h.count(uid) == 3
    run(scenario())


def test_user_with_one_project_sends_two_at_once_both_succeed():
    async def scenario():
        async with harness() as h:
            uid = await h.new_user(projects=1)
            async with h.hold_user_lock(uid):
                tasks = [asyncio.create_task(h.create(uid, f"Parallel {i}")) for i in range(2)]
                await h.wait_for_lock_waiters(2)
            responses = await asyncio.gather(*tasks)
            assert codes(responses) == [201, 201]
            assert await h.count(uid) == 3
    run(scenario())


def test_requests_from_different_users_do_not_block_each_other():
    async def scenario():
        async with harness() as h:
            busy_user = await h.new_user()
            other_user = await h.new_user()
            async with h.hold_user_lock(busy_user):
                blocked = asyncio.create_task(h.create(busy_user, "Waits"))
                await h.wait_for_lock_waiters(1)
                started = time.monotonic()
                free = await h.create(other_user, "Does not wait")
                assert free.status_code == 201
                assert time.monotonic() - started < 10
                assert not blocked.done(), "the locked user's request should still be waiting"
            assert (await blocked).status_code == 201
    run(scenario())


def test_failed_creation_leaves_no_partial_project_and_no_open_transaction(monkeypatch):
    real_insert = service._insert

    async def insert_then_fail(session, project):
        await real_insert(session, project)  # the row is written inside the transaction ...
        raise RuntimeError("simulated crash after insert")  # ... then something goes wrong

    async def scenario():
        async with harness() as h:
            uid = await h.new_user(projects=1)
            monkeypatch.setattr(service, "_insert", insert_then_fail)
            crashed = await h.create(uid, "Never saved")
            monkeypatch.setattr(service, "_insert", real_insert)
            assert crashed.status_code == 500
            assert await h.count(uid) == 1
            assert await h.open_transactions() == 0

            # A database error after the lock (duplicate name) is also rolled back cleanly
            assert (await h.create(uid, "Shop")).status_code == 201
            duplicate = await h.create(uid, "shop")
            assert duplicate.status_code == 409
            assert duplicate.json()["detail"]["code"] == "project_name_taken"
            assert await h.count(uid) == 2
            assert await h.open_transactions() == 0

            # The user can still create the last allowed project afterwards: nothing was left locked
            assert (await h.create(uid, "Third")).status_code == 201
            assert await h.count(uid) == 3
    run(scenario())


# --- extra cases ---------------------------------------------------------------------------------

def test_many_simultaneous_creates_never_exceed_the_limit():
    async def scenario():
        async with harness() as h:
            uid = await h.new_user()
            responses = await asyncio.gather(*(h.create(uid, f"Burst {i}") for i in range(6)))
            assert codes(responses) == [201, 201, 201, 409, 409, 409]
            assert await h.count(uid) == 3
    run(scenario())


def test_missing_user_gets_404_and_nothing_is_written():
    async def scenario():
        async with harness() as h:
            ghost = uuid.uuid4()
            response = await h.create(ghost, "Orphan")
            assert response.status_code == 404
            assert response.json()["detail"]["code"] == "user_not_found"
            assert await h.count(ghost) == 0
    run(scenario())


def test_lock_timeout_gives_503_and_writes_nothing(monkeypatch):
    async def scenario():
        async with harness() as h:
            uid = await h.new_user(projects=1)
            monkeypatch.setattr(service, "LOCK_TIMEOUT_MS", 300)
            async with h.hold_user_lock(uid):
                response = await h.create(uid, "Too slow")
            assert response.status_code == 503
            assert response.headers["retry-after"] == "1"
            assert await h.count(uid) == 1
            assert await h.open_transactions() == 0
    run(scenario())


def test_delete_frees_a_slot_and_cannot_touch_other_users_projects():
    async def scenario():
        async with harness() as h:
            owner = await h.new_user(projects=3)
            stranger = await h.new_user()
            listed = (await h.client.get("/api/projects", headers={"x-test-user": str(owner)})).json()
            assert len(listed) == 3
            target = listed[0]["id"]

            denied = await h.client.delete(f"/api/projects/{target}", headers={"x-test-user": str(stranger)})
            assert denied.status_code == 404
            assert await h.count(owner) == 3

            deleted = await h.client.delete(f"/api/projects/{target}", headers={"x-test-user": str(owner)})
            assert deleted.status_code == 204
            assert (await h.create(owner, "Replacement")).status_code == 201
            assert await h.count(owner) == 3
    run(scenario())


# --- the database safety net (trigger), bypassing the API ---------------------------------------

async def _raw_insert(engine, uid: uuid.UUID, name: str, isolation: str = "READ COMMITTED") -> str:
    """Insert straight into projects, as a careless future code path might. Returns the outcome."""
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level=isolation)
        try:
            async with conn.begin():
                await conn.execute(text("INSERT INTO projects (owner_id, name) VALUES (:o, :n)"), {"o": uid, "n": name})
            return "ok"
        except DBAPIError as error:
            return sqlstate(error)


def test_trigger_rejects_a_direct_fourth_insert():
    async def scenario():
        async with harness() as h:
            uid = await h.new_user(projects=3)
            assert await _raw_insert(h.engine, uid, "Direct") == "FG001"
            assert await h.count(uid) == 3
    run(scenario())


def test_trigger_is_safe_for_simultaneous_direct_inserts():
    async def scenario():
        async with harness() as h:
            uid = await h.new_user(projects=2)
            async with h.hold_user_lock(uid):
                tasks = [asyncio.create_task(_raw_insert(h.engine, uid, f"Direct {i}")) for i in range(2)]
                await h.wait_for_lock_waiters(2, statement="INSERT INTO projects")
            assert sorted(await asyncio.gather(*tasks)) == ["FG001", "ok"]
            assert await h.count(uid) == 3
    run(scenario())


def test_trigger_refuses_repeatable_read():
    async def scenario():
        async with harness() as h:
            uid = await h.new_user()
            assert await _raw_insert(h.engine, uid, "Snapshot", isolation="REPEATABLE READ") == "FG002"
            assert await h.count(uid) == 0
    run(scenario())


def test_limit_in_migration_matches_service():
    path = MIGRATIONS / "versions" / "0001_users_and_projects.py"
    spec = importlib.util.spec_from_file_location("migration_0001", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.PROJECT_LIMIT == service.MAX_PROJECTS_PER_USER
