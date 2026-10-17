"""
Integration tests for sign-in (D-176 - D-178) on a real PostgreSQL database, through the HTTP API.
Skipped unless TEST_DATABASE_URL is set. Each test registers its own users and deletes them.
The refresh cookie is sent by hand in every call, so each test controls exactly which token is used.
"""
import asyncio
import uuid
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from backend.db.session import get_session
from backend.routes.auth import REFRESH_COOKIE
from backend.routes.auth import router as auth_router
from backend.routes.projects import router as projects_router
from backend.services import auth as service
from pg_support import EmptyGraph, migrate_test_database, new_engine, requires_db, session_dependency, wait_for_lock_waiters

pytestmark = requires_db
PASSWORD = "correct horse battery"


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    migrate_test_database()


class Harness:
    def __init__(self, engine, client):
        self.engine = engine
        self.client = client
        self.emails: list[str] = []

    def new_email(self) -> str:
        email = f"auth-test-{uuid.uuid4()}@example.com"
        self.emails.append(email)
        return email

    async def register(self, email: str | None = None, password: str = PASSWORD) -> httpx.Response:
        return await self.post("/api/auth/register",
                               json={"email": email or self.new_email(), "password": password, "display_name": "Test"})

    async def login(self, email: str, password: str = PASSWORD) -> httpx.Response:
        return await self.post("/api/auth/login", json={"email": email, "password": password})

    async def refresh(self, token: str | None) -> httpx.Response:
        return await self.post("/api/auth/refresh", cookie=token)

    async def post(self, path: str, json: dict | None = None, cookie: str | None = None,
                   bearer: str | None = None) -> httpx.Response:
        headers = {}
        if cookie is not None:
            headers["cookie"] = f"{REFRESH_COOKIE}={cookie}"
        if bearer is not None:
            headers["authorization"] = f"Bearer {bearer}"
        self.client.cookies.clear()
        return await self.client.post(path, json=json, headers=headers)

    async def get(self, path: str, bearer: str | None = None) -> httpx.Response:
        self.client.cookies.clear()
        headers = {"authorization": f"Bearer {bearer}"} if bearer else {}
        return await self.client.get(path, headers=headers)

    async def sql(self, statement: str, **params):
        async with self.engine.begin() as conn:
            result = await conn.execute(text(statement), params)
            return result.first() if result.returns_rows else None


def refresh_cookie(response: httpx.Response) -> str:
    return response.cookies[REFRESH_COOKIE]


@asynccontextmanager
async def harness():
    engine = new_engine()
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.state.forge_graph = EmptyGraph()
    app.dependency_overrides[get_session] = session_dependency(engine)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        h = Harness(engine, client)
        try:
            yield h
        finally:
            if h.emails:
                await h.sql("DELETE FROM users WHERE email = ANY(:emails)", emails=h.emails)
            await engine.dispose()


def run(coro):
    return asyncio.run(coro)


# --- register ------------------------------------------------------------------------------------

def test_register_signs_in_with_safe_cookie_and_argon2_hash():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            response = await h.register(email)
            assert response.status_code == 201
            body = response.json()
            assert body["token_type"] == "bearer" and 0 < body["expires_in"] <= 15 * 60
            assert body["user"]["email"] == email
            assert "refresh" not in str(body).lower().replace("refresh_token", "")
            assert response.headers["cache-control"] == "no-store"

            cookie = response.headers["set-cookie"].lower()
            assert f"{REFRESH_COOKIE}=" in cookie and "httponly" in cookie
            assert "path=/api/auth" in cookie and "samesite=lax" in cookie and "max-age=" in cookie

            me = await h.get("/api/auth/me", bearer=body["access_token"])
            assert me.status_code == 200 and me.json()["email"] == email

            stored = await h.sql("SELECT password_hash FROM users WHERE email = :e", e=email)
            assert stored.password_hash.startswith("$argon2id$") and PASSWORD not in stored.password_hash
            token_rows = await h.sql("SELECT count(*) AS n FROM refresh_tokens t JOIN users u ON u.id = t.user_id "
                                     "WHERE u.email = :e AND t.token_hash <> :raw", e=email, raw=refresh_cookie(response))
            assert token_rows.n == 1  # stored as a hash, never the token itself
    run(scenario())


def test_register_refuses_same_email_in_other_case_and_bad_input():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            assert (await h.register(email)).status_code == 201
            duplicate = await h.register(email.upper())
            assert duplicate.status_code == 409 and duplicate.json()["detail"]["code"] == "email_taken"
            assert (await h.register(password="short")).status_code == 422
            assert (await h.register(password=" " * 12)).status_code == 422
            assert (await h.register(email="not-an-email")).status_code == 422
    run(scenario())


# --- login ---------------------------------------------------------------------------------------

def test_login_works_with_any_email_case():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            await h.register(email)
            response = await h.login(email.upper())
            assert response.status_code == 200 and refresh_cookie(response)
            last_login = await h.sql("SELECT last_login_at FROM users WHERE email = :e", e=email)
            assert last_login.last_login_at is not None
    run(scenario())


def test_wrong_password_and_unknown_email_look_the_same():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            await h.register(email)
            wrong = await h.login(email, "not the password")
            unknown = await h.login(f"nobody-{uuid.uuid4()}@example.com", "not the password")
            assert wrong.status_code == unknown.status_code == 401
            assert wrong.json() == unknown.json()
    run(scenario())


def test_five_wrong_passwords_lock_the_account():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            await h.register(email)
            for _ in range(service.MAX_FAILED_LOGINS):
                assert (await h.login(email, "wrong password")).status_code == 401
            locked = await h.login(email)  # even the right password is refused while locked
            assert locked.status_code == 429 and locked.json()["detail"]["code"] == "account_locked"
            assert 0 < int(locked.headers["retry-after"]) <= 15 * 60

            await h.sql("UPDATE users SET locked_until = now() - interval '1 second' WHERE email = :e", e=email)
            assert (await h.login(email)).status_code == 200
            row = await h.sql("SELECT failed_logins, locked_until FROM users WHERE email = :e", e=email)
            assert row.failed_logins == 0 and row.locked_until is None
    run(scenario())


def test_simultaneous_wrong_passwords_are_all_counted():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            await h.register(email)
            responses = await asyncio.gather(*(h.login(email, f"wrong {i}") for i in range(service.MAX_FAILED_LOGINS)))
            assert sorted(r.status_code for r in responses) == [401] * service.MAX_FAILED_LOGINS
            assert (await h.login(email)).status_code == 429  # no attempt was lost to a race
    run(scenario())


def test_inactive_account_cannot_sign_in():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            await h.register(email)
            await h.sql("UPDATE users SET is_active = false WHERE email = :e", e=email)
            assert (await h.login(email)).status_code == 401
    run(scenario())


# --- access token --------------------------------------------------------------------------------

def test_protected_routes_need_a_valid_access_token():
    async def scenario():
        async with harness() as h:
            registered = await h.register()
            access, refresh = registered.json()["access_token"], refresh_cookie(registered)
            assert (await h.get("/api/auth/me")).status_code == 401
            assert (await h.get("/api/auth/me", bearer="garbage")).status_code == 401
            assert (await h.get("/api/auth/me", bearer=refresh)).status_code == 401  # wrong token type
            assert (await h.get("/api/projects")).status_code == 401

            created = await h.post("/api/projects", json={"name": "My shop"}, bearer=access)
            assert created.status_code == 201
            listed = await h.get("/api/projects", bearer=access)
            assert [p["name"] for p in listed.json()] == ["My shop"]
    run(scenario())


# --- refresh rotation and reuse detection --------------------------------------------------------

def test_refresh_rotates_the_token():
    async def scenario():
        async with harness() as h:
            first = refresh_cookie(await h.register())
            rotated = await h.refresh(first)
            assert rotated.status_code == 200
            second = refresh_cookie(rotated)
            assert second != first
            assert (await h.get("/api/auth/me", bearer=rotated.json()["access_token"])).status_code == 200

            # The old token used again within seconds (another tab) gets "try again" (409); the
            # browser's new cookie is left alone and the session survives
            stale = await h.refresh(first)
            assert stale.status_code == 409 and stale.json()["detail"]["code"] == "refresh_in_progress"
            assert "set-cookie" not in stale.headers
            assert (await h.refresh(second)).status_code == 200
    run(scenario())


def test_reusing_an_old_refresh_token_revokes_the_whole_session(monkeypatch):
    monkeypatch.setattr(service, "ROTATION_GRACE", service.ROTATION_GRACE * 0)

    async def scenario():
        async with harness() as h:
            stolen = refresh_cookie(await h.register())
            # (grace period 0: a replay is never mistaken for a second tab)
            current = refresh_cookie(await h.refresh(stolen))  # the real user moves on
            assert (await h.refresh(stolen)).status_code == 401  # the thief replays the old token
            assert (await h.refresh(current)).status_code == 401  # so the real session is ended too
    run(scenario())


def test_two_simultaneous_refreshes_with_one_token():
    async def scenario():
        async with harness() as h:
            token = refresh_cookie(await h.register())
            hashed = service.security.hash_token_id(service.security.decode_refresh_token(token).jti)
            async with h.engine.connect() as conn:
                trans = await conn.begin()
                await conn.execute(text("SELECT id FROM refresh_tokens WHERE token_hash = :t FOR UPDATE"), {"t": hashed})
                tasks = [asyncio.create_task(h.refresh(token)) for _ in range(2)]
                await wait_for_lock_waiters(h.engine, 2, "refresh_tokens")
                await trans.rollback()
            responses = await asyncio.gather(*tasks)
            assert sorted(r.status_code for r in responses) == [200, 409]
            winner = next(r for r in responses if r.status_code == 200)
            assert (await h.refresh(refresh_cookie(winner))).status_code == 200  # session still alive
    run(scenario())


def test_expired_or_missing_refresh_token_is_refused():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            token = refresh_cookie(await h.register(email))
            assert (await h.refresh(None)).status_code == 401
            assert (await h.refresh("garbage")).status_code == 401
            await h.sql("UPDATE refresh_tokens SET expires_at = now() - interval '1 second' "
                        "WHERE user_id = (SELECT id FROM users WHERE email = :e)", e=email)
            assert (await h.refresh(token)).status_code == 401
    run(scenario())


# --- logout and deleted accounts -----------------------------------------------------------------

def test_logout_ends_the_session_and_clears_the_cookie():
    async def scenario():
        async with harness() as h:
            token = refresh_cookie(await h.register())
            out = await h.post("/api/auth/logout", cookie=token)
            assert out.status_code == 204
            assert "max-age=0" in out.headers["set-cookie"].lower() or 'forge_refresh=""' in out.headers["set-cookie"]
            assert (await h.refresh(token)).status_code == 401
            assert (await h.post("/api/auth/logout")).status_code == 204  # harmless without a cookie
    run(scenario())


def test_deleted_account_cannot_refresh_or_create_projects():
    async def scenario():
        async with harness() as h:
            email = h.new_email()
            registered = await h.register(email)
            access, token = registered.json()["access_token"], refresh_cookie(registered)
            await h.sql("DELETE FROM users WHERE email = :e", e=email)
            assert (await h.refresh(token)).status_code == 401
            assert (await h.get("/api/auth/me", bearer=access)).status_code == 401
            created = await h.post("/api/projects", json={"name": "Ghost"}, bearer=access)
            assert created.status_code == 404 and created.json()["detail"]["code"] == "user_not_found"
    run(scenario())
