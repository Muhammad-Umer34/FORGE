"""
Integration tests for email verification and password reset (D-185 - D-188) on a real PostgreSQL
database. Emails are captured in an outbox, never sent. Skipped unless TEST_DATABASE_URL is set.
"""
import asyncio
import re
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
from backend.services import email_flows
from pg_support import EmptyGraph, migrate_test_database, new_engine, outbox, requires_db, session_dependency  # noqa: F401

pytestmark = requires_db
PASSWORD = "correct horse battery"
NEW_PASSWORD = "a brand new passphrase"


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    migrate_test_database()


def link_token(mail) -> str:
    return re.search(r"token=([A-Za-z0-9_-]+)", mail.text).group(1)


class Harness:
    def __init__(self, engine, client, mails):
        self.engine, self.client, self.mails = engine, client, mails
        self.emails: list[str] = []

    async def post(self, path, json=None, bearer=None, cookie=None):
        headers = {}
        if bearer:
            headers["authorization"] = f"Bearer {bearer}"
        if cookie:
            headers["cookie"] = f"{REFRESH_COOKIE}={cookie}"
        self.client.cookies.clear()
        return await self.client.post(path, json=json, headers=headers)

    async def register(self):
        email = f"mail-test-{uuid.uuid4()}@example.com"
        self.emails.append(email)
        response = await self.post("/api/auth/register", {"email": email, "password": PASSWORD, "display_name": "Ayesha"})
        assert response.status_code == 201
        return email, response

    async def sql(self, statement, **params):
        async with self.engine.begin() as conn:
            result = await conn.execute(text(statement), params)
            return result.first() if result.returns_rows else None


@asynccontextmanager
async def harness(mails):
    engine = new_engine()
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.state.forge_graph = EmptyGraph()
    app.dependency_overrides[get_session] = session_dependency(engine)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        h = Harness(engine, client, mails)
        try:
            yield h
        finally:
            if h.emails:
                await h.sql("DELETE FROM users WHERE email = ANY(:emails)", emails=h.emails)
            await engine.dispose()


def run(coro):
    return asyncio.run(coro)


# --- verification ---------------------------------------------------------------------------------

def test_register_sends_a_link_that_unlocks_projects(outbox):
    async def scenario():
        async with harness(outbox) as h:
            email, registered = await h.register()
            body = registered.json()
            assert body["user"]["email_verified"] is False
            assert len(outbox) == 1 and outbox[0].to == email and "/verify-email?token=" in outbox[0].text
            token = link_token(outbox[0])
            stored = await h.sql("SELECT t.token_hash FROM auth_tokens t JOIN users u ON u.id = t.user_id WHERE u.email = :e", e=email)
            assert stored.token_hash != token and len(stored.token_hash) == 64  # only the hash is stored

            refused = await h.post("/api/projects", {"name": "Shop"}, bearer=body["access_token"])
            assert refused.status_code == 403 and refused.json()["detail"]["code"] == "email_not_verified"

            verified = await h.post("/api/auth/verify-email", {"token": token})
            assert verified.status_code == 200 and verified.json()["email_verified"] is True

            renewed = await h.post("/api/auth/refresh", cookie=registered.cookies[REFRESH_COOKIE])
            assert renewed.json()["user"]["email_verified"] is True
            created = await h.post("/api/projects", {"name": "Shop"}, bearer=renewed.json()["access_token"])
            assert created.status_code == 201
    run(scenario())


def test_a_link_works_once_and_bad_links_are_refused(outbox):
    async def scenario():
        async with harness(outbox) as h:
            email, _ = await h.register()
            token = link_token(outbox[0])
            assert (await h.post("/api/auth/verify-email", {"token": token})).status_code == 200
            again = await h.post("/api/auth/verify-email", {"token": token})
            assert again.status_code == 400 and again.json()["detail"]["code"] == "invalid_link"
            assert (await h.post("/api/auth/verify-email", {"token": "x" * 43})).status_code == 400

            email2, _ = await h.register()
            await h.sql("UPDATE auth_tokens SET expires_at = now() - interval '1 hour' "
                        "WHERE user_id = (SELECT id FROM users WHERE email = :e)", e=email2)
            assert (await h.post("/api/auth/verify-email", {"token": link_token(outbox[1])})).status_code == 400
    run(scenario())


def test_two_clicks_at_once_verify_only_once(outbox):
    async def scenario():
        async with harness(outbox) as h:
            await h.register()
            token = link_token(outbox[0])
            results = await asyncio.gather(*(h.post("/api/auth/verify-email", {"token": token}) for _ in range(2)))
            assert sorted(r.status_code for r in results) == [200, 400]
    run(scenario())


def test_resend_replaces_the_old_link_and_is_limited(outbox):
    async def scenario():
        async with harness(outbox) as h:
            email, registered = await h.register()
            access = registered.json()["access_token"]
            first = link_token(outbox[0])
            resent = await h.post("/api/auth/resend-verification", bearer=access)
            assert resent.status_code == 202 and len(outbox) == 2
            assert (await h.post("/api/auth/verify-email", {"token": first})).status_code == 400  # replaced

            # One link at sign-up plus two resends reach the limit of 3 per hour
            assert (await h.post("/api/auth/resend-verification", bearer=access)).status_code == 202
            limited = await h.post("/api/auth/resend-verification", bearer=access)
            assert limited.status_code == 429 and limited.json()["detail"]["code"] == "too_many_emails"

            assert (await h.post("/api/auth/verify-email", {"token": link_token(outbox[-1])})).status_code == 200
            done = await h.post("/api/auth/resend-verification", bearer=access)
            assert done.status_code == 409 and done.json()["detail"]["code"] == "already_verified"
    run(scenario())


# --- password reset -------------------------------------------------------------------------------

def test_forgot_password_gives_the_same_answer_for_unknown_emails(outbox):
    async def scenario():
        async with harness(outbox) as h:
            email, _ = await h.register()
            outbox.clear()
            known = await h.post("/api/auth/forgot-password", {"email": email.upper()})
            unknown = await h.post("/api/auth/forgot-password", {"email": f"nobody-{uuid.uuid4()}@example.com"})
            assert known.status_code == unknown.status_code == 202
            assert known.json() == unknown.json()
            assert [m.to for m in outbox] == [email] and "/reset-password?token=" in outbox[0].text
    run(scenario())


def test_reset_changes_the_password_and_signs_out_everywhere(outbox):
    async def scenario():
        async with harness(outbox) as h:
            email, registered = await h.register()
            old_refresh = registered.cookies[REFRESH_COOKIE]
            await h.sql("UPDATE users SET failed_logins = 3, locked_until = now() + interval '10 minutes' WHERE email = :e", e=email)
            await h.post("/api/auth/forgot-password", {"email": email})
            token = link_token(outbox[-1])

            assert (await h.post("/api/auth/reset-password", {"token": token, "password": "short"})).status_code == 422
            done = await h.post("/api/auth/reset-password", {"token": token, "password": NEW_PASSWORD})
            assert done.status_code == 200
            assert (await h.post("/api/auth/reset-password", {"token": token, "password": NEW_PASSWORD})).status_code == 400

            assert (await h.post("/api/auth/refresh", cookie=old_refresh)).status_code == 401  # signed out everywhere
            assert (await h.post("/api/auth/login", {"email": email, "password": PASSWORD})).status_code == 401
            signed_in = await h.post("/api/auth/login", {"email": email, "password": NEW_PASSWORD})
            assert signed_in.status_code == 200  # lockout cleared
            assert signed_in.json()["user"]["email_verified"] is True  # the emailed link proved the address
    run(scenario())


def test_reset_links_expire_and_are_limited(outbox):
    async def scenario():
        async with harness(outbox) as h:
            email, _ = await h.register()
            outbox.clear()
            for _ in range(email_flows.MAX_EMAILS_PER_HOUR + 1):
                assert (await h.post("/api/auth/forgot-password", {"email": email})).status_code == 202
            assert len(outbox) == email_flows.MAX_EMAILS_PER_HOUR  # the extra request sent nothing
            await h.sql("UPDATE auth_tokens SET expires_at = now() - interval '1 hour' "
                        "WHERE user_id = (SELECT id FROM users WHERE email = :e)", e=email)
            expired = await h.post("/api/auth/reset-password", {"token": link_token(outbox[-1]), "password": NEW_PASSWORD})
            assert expired.status_code == 400
    run(scenario())
