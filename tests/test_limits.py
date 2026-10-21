"""
Tests for the cost and abuse limits (D-189 - D-194). The limiter, request, sign-up, email and sign-in
limits run on a real PostgreSQL database (skipped unless TEST_DATABASE_URL is set); the body-size
check, the client-address rule and the website reader cap need no database.
"""
import asyncio
import subprocess
import threading
import time
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, File, UploadFile
from sqlalchemy import text

from agents import reference_style
from backend.core.body_limit import BodySizeLimit
from backend.core.config import settings
from backend.core.deps import client_ip, get_current_user_id, get_verified_user_id
from backend.db.session import get_session, make_sessionmaker
from backend.routes.auth import router as auth_router
from backend.routes.projects import router as projects_router
from backend.routes.requests import router as requests_router
from backend.services import limits
from backend.services import requests as request_service
from pg_support import EmptyGraph, migrate_test_database, new_engine, outbox, requires_db, session_dependency  # noqa: F401

PASSWORD = "correct horse battery"


def run(coro):
    return asyncio.run(coro)


def unique_ip() -> str:
    """A different documentation address (198.18.0.0/15) per call, so counters never collide."""
    n = uuid.uuid4().int
    return f"198.{18 + n % 2}.{(n >> 8) % 256}.{(n >> 16) % 254 + 1}"


# ======================================================================== no database needed

def test_body_size_check_refuses_large_bodies_before_they_are_read():
    reached = []
    app = FastAPI()

    @app.post("/x/image")
    async def image(file: UploadFile = File(...)):
        reached.append(file.filename)
        return {"ok": True}

    @app.post("/x/json")
    async def json_route(body: dict):
        reached.append("json")
        return {"ok": True}

    app.add_middleware(BodySizeLimit)

    async def scenario():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            big = await client.post("/x/image", files={"file": ("a.png", b"\0" * (settings.MAX_IMAGE_UPLOAD_BYTES + 10), "image/png")})
            assert big.status_code == 413 and big.json()["detail"]["code"] == "too_large"
            small = await client.post("/x/image", files={"file": ("b.png", b"\0" * 1000, "image/png")})
            assert small.status_code == 200
            assert (await client.post("/x/json", json={"a": "x" * (settings.MAX_JSON_BODY_BYTES + 10)})).status_code == 413

            async def chunks():  # no Content-Length: counted as it arrives
                for _ in range(40):
                    yield b"x" * 4096
            streamed = await client.post("/x/json", content=chunks(), headers={"content-type": "application/json"})
            assert streamed.status_code == 413
        assert reached == ["b.png"]  # the oversized bodies never reached a route
    run(scenario())


def _fake_request(host: str, forwarded: str | None = None):
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    return SimpleNamespace(client=SimpleNamespace(host=host), headers=headers)


def test_forwarded_address_is_trusted_only_from_this_machine():
    assert client_ip(_fake_request("127.0.0.1", "203.0.113.5, 10.0.0.1")) == "203.0.113.5"
    assert client_ip(_fake_request("::1", "203.0.113.6")) == "203.0.113.6"
    assert client_ip(_fake_request("192.168.1.20", "203.0.113.7")) == "192.168.1.20"  # could be faked
    assert client_ip(_fake_request("127.0.0.1", "not-an-address")) == "127.0.0.1"
    assert client_ip(_fake_request("127.0.0.1")) == "127.0.0.1"
    assert client_ip(_fake_request("127.0.0.1", "::ffff:203.0.113.8")) == "203.0.113.8"  # how Node reports IPv4


def test_website_reader_runs_at_most_the_allowed_browsers(monkeypatch):
    monkeypatch.setattr(reference_style, "_browsers", threading.BoundedSemaphore(1))
    monkeypatch.setattr(reference_style, "READER_WAIT_S", 0.3)
    monkeypatch.setattr(reference_style, "check_url", lambda url: url)

    def slow_browser(url):
        time.sleep(1.0)
        return subprocess.CompletedProcess([], 0, stdout='{"error": "test page"}', stderr="")

    monkeypatch.setattr(reference_style, "_run_browser", slow_browser)
    outcomes = []

    def read():
        try:
            reference_style.read_reference("https://example.com")
        except reference_style.ReferenceSiteError as error:
            outcomes.append(str(error))

    threads = [threading.Thread(target=read) for _ in range(2)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert sorted(outcomes) == sorted(["test page", "FORGE is busy reading other websites. Please try again in a minute."])


def test_one_step_at_a_time_per_request():
    async def scenario():
        async with request_service.one_step_at_a_time("req_a"):
            with pytest.raises(request_service.RunInProgress):
                async with request_service.one_step_at_a_time("req_a"):
                    pass
            async with request_service.one_step_at_a_time("req_b"):  # other requests are not blocked
                pass
        async with request_service.one_step_at_a_time("req_a"):  # free again afterwards
            pass
    run(scenario())


# ======================================================================== PostgreSQL

pg = requires_db


@pytest.fixture(scope="module")
def migrated():
    migrate_test_database()


@pg
def test_limiter_counts_simultaneous_hits_exactly(migrated):
    async def scenario():
        engine = new_engine()
        maker = make_sessionmaker(engine)
        key = f"test:{uuid.uuid4()}"

        async def one():
            async with maker() as session:
                return await limits.try_take(session, key, 10, limits.HOUR)

        results = await asyncio.gather(*(one() for _ in range(20)))
        assert results.count(True) == 10

        # All or nothing: a full rule means the other rule is not used either
        other = f"test:{uuid.uuid4()}"
        async with maker() as session:
            with pytest.raises(limits.RateLimited):
                await limits.take(session, (other, 5, limits.HOUR), (key, 10, limits.HOUR))
            async with session.begin():
                assert await limits.current(session, other, limits.HOUR) == 0
            await session.execute(text("DELETE FROM rate_limits WHERE key = ANY(:k)"), {"k": [key, other]})
            await session.commit()
        await engine.dispose()
    run(scenario())


class SlowGraph(EmptyGraph):
    """Stands in for the agent: a paused question or confirmation, with slow steps."""

    def __init__(self, payload):
        super().__init__()
        self.payload, self.runs = payload, 0

    async def ainvoke(self, graph_input, config):
        self.runs += 1
        await asyncio.sleep(0.5)

    async def aget_state(self, config):
        await asyncio.sleep(0.3)
        return SimpleNamespace(values={"run": True}, interrupts=(SimpleNamespace(value=self.payload),))


@asynccontextmanager
async def app_harness(graph=None):
    engine = new_engine()
    app = FastAPI()
    for router in (auth_router, projects_router, requests_router):
        app.include_router(router)
    app.add_middleware(BodySizeLimit)
    app.state.forge_graph = graph or EmptyGraph()
    app.dependency_overrides[get_session] = session_dependency(engine)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    users: list[uuid.UUID] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        h = SimpleNamespace(engine=engine, client=client, app=app, users=users, emails=[])
        try:
            yield h
        finally:
            async with engine.begin() as conn:
                if users:
                    await conn.execute(text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": users})
                if h.emails:
                    await conn.execute(text("DELETE FROM users WHERE email = ANY(:e)"), {"e": h.emails})
            await engine.dispose()


async def verified_user_with_project(h) -> tuple[uuid.UUID, uuid.UUID]:
    uid, pid = uuid.uuid4(), uuid.uuid4()
    async with h.engine.begin() as conn:
        await conn.execute(text("INSERT INTO users (id, email, password_hash, display_name, email_verified_at) "
                                "VALUES (:id, :e, '!', 'T', now())"), {"id": uid, "e": f"limit-{uid}@example.com"})
        await conn.execute(text("INSERT INTO projects (id, owner_id, name) VALUES (:p, :o, 'P')"), {"p": pid, "o": uid})
        rid = f"req_{uuid.uuid4().hex[:12]}"
        await conn.execute(text("INSERT INTO requests (id, project_id, prompt, status) VALUES (:r, :p, 'x', 'needs_clarification')"),
                           {"r": rid, "p": pid})
    h.users.append(uid)
    h.app.dependency_overrides[get_verified_user_id] = lambda: uid
    h.app.dependency_overrides[get_current_user_id] = lambda: uid
    return pid, rid


@pg
def test_requests_per_user_per_day(migrated, monkeypatch):
    monkeypatch.setattr(settings, "LIMIT_REQUESTS_PER_USER_DAY", 2)

    async def scenario():
        async with app_harness(SlowGraph({"type": "question"})) as h:
            pid, _ = await verified_user_with_project(h)
            for _ in range(2):
                await h.client.post(f"/api/projects/{pid}/requests", json={"prompt": "A bakery website"})
            third = await h.client.post(f"/api/projects/{pid}/requests", json={"prompt": "A bakery website"})
            assert third.status_code == 429 and int(third.headers["retry-after"]) > 0
            assert h.app.state.forge_graph.runs == 2  # the third never reached the model
    run(scenario())


class BrokenGraph(EmptyGraph):
    async def ainvoke(self, graph_input, config):
        raise RuntimeError("model is down")


@pg
def test_a_failed_run_is_marked_failed_and_not_counted(migrated, monkeypatch):
    monkeypatch.setattr(settings, "LIMIT_REQUESTS_PER_USER_DAY", 1)

    async def scenario():
        async with app_harness(BrokenGraph()) as h:
            pid, _ = await verified_user_with_project(h)
            for _ in range(2):  # the second would be 429 if the first had been counted
                r = await h.client.post(f"/api/projects/{pid}/requests", json={"prompt": "A bakery website"})
                assert r.status_code == 500
            async with h.engine.connect() as conn:
                statuses = (await conn.execute(text("SELECT status FROM requests WHERE prompt = 'A bakery website' "
                                                    "AND project_id = :p"), {"p": pid})).scalars().all()
            assert statuses == ["failed", "failed"]
    run(scenario())


@pg
def test_a_double_answer_runs_the_agent_once(migrated):
    async def scenario():
        async with app_harness(SlowGraph({"type": "question"})) as h:
            pid, rid = await verified_user_with_project(h)
            body = {"question_id": "q1", "kind": "you_decide"}
            first, second = await asyncio.gather(
                h.client.post(f"/api/projects/{pid}/requests/{rid}/answer", json=body),
                h.client.post(f"/api/projects/{pid}/requests/{rid}/answer", json=body),
            )
            assert 409 in (first.status_code, second.status_code)
            assert h.app.state.forge_graph.runs <= 1
    run(scenario())


@pg
def test_website_and_image_reads_are_limited_per_user(migrated, monkeypatch):
    monkeypatch.setattr(settings, "LIMIT_WEBSITE_READS_PER_USER_DAY", 1)
    monkeypatch.setattr(settings, "LIMIT_IMAGE_READS_PER_USER_HOUR", 1)
    payload = {"type": "confirmation", "actions": ["theme_source"], "theme_sources_left": {"website": 3}}

    async def scenario():
        async with app_harness(SlowGraph(payload)) as h:
            pid, rid = await verified_user_with_project(h)
            body = {"decision": "theme_source", "theme_source": {"kind": "website", "url": "example.com"}}
            assert (await h.client.post(f"/api/projects/{pid}/requests/{rid}/confirmation", json=body)).status_code != 429
            assert (await h.client.post(f"/api/projects/{pid}/requests/{rid}/confirmation", json=body)).status_code == 429

            png = ("logo.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 100, "image/png")
            assert (await h.client.post(f"/api/projects/{pid}/requests/{rid}/image?kind=logo", files={"file": png})).status_code != 429
            assert (await h.client.post(f"/api/projects/{pid}/requests/{rid}/image?kind=logo", files={"file": png})).status_code == 429
    run(scenario())


async def register(h, ip: str, email: str | None = None):
    email = email or f"limit-{uuid.uuid4()}@example.com"
    h.emails.append(email)
    h.client.cookies.clear()
    return await h.client.post("/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": "T"},
                               headers={"x-forwarded-for": ip})


async def login(h, ip: str, email: str, password: str = PASSWORD):
    h.client.cookies.clear()
    return await h.client.post("/api/auth/login", json={"email": email, "password": password}, headers={"x-forwarded-for": ip})


@pg
def test_signups_are_limited_per_address(migrated, monkeypatch, outbox):
    monkeypatch.setattr(settings, "LIMIT_SIGNUPS_PER_IP_HOUR", 2)

    async def scenario():
        async with app_harness() as h:
            ip = unique_ip()
            assert (await register(h, ip)).status_code == 201
            assert (await register(h, ip)).status_code == 201
            third = await register(h, ip)
            assert third.status_code == 429 and third.json()["detail"]["code"] == "too_many_attempts"
            assert (await register(h, unique_ip())).status_code == 201  # another address is not affected
    run(scenario())


@pg
def test_email_cap_creates_the_account_but_says_the_email_was_not_sent(migrated, monkeypatch, outbox):
    async def scenario():
        async with app_harness() as h:
            async with make_sessionmaker(h.engine)() as session, session.begin():
                sent_today = await limits.current(session, "emails:all", limits.DAY)
            monkeypatch.setattr(settings, "LIMIT_EMAILS_PER_DAY", sent_today)  # already full
            response = await register(h, unique_ip())
            assert response.status_code == 201
            assert "could not send" in response.json()["notice"]
            assert outbox == []
    run(scenario())


@pg
def test_forgot_password_is_limited_per_address(migrated, monkeypatch, outbox):
    monkeypatch.setattr(settings, "LIMIT_FORGOT_PER_IP_HOUR", 2)

    async def scenario():
        async with app_harness() as h:
            ip = unique_ip()
            for _ in range(2):
                r = await h.client.post("/api/auth/forgot-password", json={"email": "x@example.com"}, headers={"x-forwarded-for": ip})
                assert r.status_code == 202
            r = await h.client.post("/api/auth/forgot-password", json={"email": "x@example.com"}, headers={"x-forwarded-for": ip})
            assert r.status_code == 429
    run(scenario())


@pg
def test_wrong_passwords_block_that_address_not_the_owner(migrated, outbox):
    async def scenario():
        async with app_harness() as h:
            email = f"limit-{uuid.uuid4()}@example.com"
            assert (await register(h, unique_ip(), email)).status_code == 201
            attacker = unique_ip()
            for _ in range(5):
                assert (await login(h, attacker, email, "wrong password")).status_code == 401
            assert (await login(h, attacker, email)).status_code == 429  # even the right password, from there
            assert (await login(h, unique_ip(), email)).status_code == 200  # the owner is not locked out
    run(scenario())


@pg
def test_guessing_from_many_addresses_locks_the_account(migrated, monkeypatch, outbox):
    monkeypatch.setattr(settings, "LIMIT_LOGIN_FAILS_PER_ACCOUNT_HOUR", 4)

    async def scenario():
        async with app_harness() as h:
            email = f"limit-{uuid.uuid4()}@example.com"
            await register(h, unique_ip(), email)
            for _ in range(4):
                assert (await login(h, unique_ip(), email, "wrong password")).status_code == 401
            locked = await login(h, unique_ip(), email)
            assert locked.status_code == 429 and locked.json()["detail"]["code"] == "account_locked"
    run(scenario())


@pg
def test_one_address_trying_many_accounts_is_blocked(migrated, monkeypatch, outbox):
    monkeypatch.setattr(settings, "LIMIT_LOGIN_FAILS_PER_IP", 3)

    async def scenario():
        async with app_harness() as h:
            email = f"limit-{uuid.uuid4()}@example.com"
            await register(h, unique_ip(), email)
            ip = unique_ip()
            for _ in range(3):
                assert (await login(h, ip, f"nobody-{uuid.uuid4()}@example.com", "guess")).status_code == 401
            assert (await login(h, ip, email)).status_code == 429
            assert (await login(h, unique_ip(), email)).status_code == 200
    run(scenario())
