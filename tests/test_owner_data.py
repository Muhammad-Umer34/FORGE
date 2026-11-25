"""The owner's dashboard (D-250) on the local PostgreSQL: only the owner reaches it, statuses follow the allowed moves,
the owner keeps their own lists, and visitors' submissions are never deleted."""
import asyncio
import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx
import psycopg
import pytest
from fastapi import FastAPI

from agents.database_generator import provision
from agents.planning import data_patterns as dp
from backend.core.config import settings
from backend.core.deps import get_verified_user_id
from backend.db.session import get_session
from backend.routes.owner_data import router
from backend.services import site_data
from backend.services.site_data import SiteDataError, Storage
from pg_support import migrate_test_database, new_engine, requires_db, session_dependency

pytestmark = requires_db
TZ = ZoneInfo("Asia/Karachi")


def _url() -> str:
    return provision.plain_url(settings.TEST_DATABASE_URL or "")


@pytest.fixture
def site():
    migrate_test_database()
    site_data.use_pool(None)
    site_data.pool(_url())
    with psycopg.connect(_url(), autocommit=True) as conn:
        user = conn.execute("INSERT INTO users (email, password_hash, display_name) VALUES (%s, 'x', 'O') RETURNING id",
                            (f"o{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]
        project = str(conn.execute("INSERT INTO projects (owner_id, name) VALUES (%s, 'Salon') RETURNING id",
                                   (user,)).fetchone()[0])
    entities, _ = dp.expand([{"pattern": "appointments", "names": {"staff": "stylists"}}])
    made = provision.provision(entities, _url(), project)
    provision.register(_url(), project, made, "req_owner")
    yield {"user": user, "project": project, "storage": Storage(project, made["schema"], made["role"], made["contract"])}
    provision.drop(_url(), project)
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))
    site_data.pool().close()
    site_data.use_pool(None)


def _booking(s):
    day = datetime.now(TZ).date() + timedelta(days=10)
    while day.weekday() == 6:
        day += timedelta(days=1)
    ids = lambda t: [r["id"] for r in site_data.list_public(s, t)]          # noqa: E731
    return site_data.submit(s, "appointments", {"client_name": "Sara", "phone": "0300 1111111",
                                                "service_id": ids("services")[0], "staff_id": ids("stylists")[0],
                                                "start_at": datetime.combine(day, time(12), TZ).isoformat()})["id"]


def test_the_summary_lists_what_the_site_keeps(site):
    s = site["storage"]
    _booking(s)
    summary = {t["name"]: t for t in site_data.owner_summary(s)}
    appt = summary["appointments"]
    assert appt["rows"] == 4 and appt["new_today"] == 1 and appt["moves"]["New"] == ["Confirmed", "Cancelled"]
    assert any(c["name"] == "phone" and c["personal"] for c in appt["columns"])
    rows = site_data.owner_rows(s, "appointments")
    assert rows["rows"][0]["client_name"] == "Sara" and rows["rows"][0]["phone"] == "0300 1111111"   # owner sees it
    assert set(rows["names"]["staff_id"].values()) >= {"Sample name 1"}


def test_status_moves_follow_the_rules(site):
    s = site["storage"]
    row = _booking(s)
    site_data.owner_update(s, "appointments", row, {"status": "Confirmed"})
    with pytest.raises(SiteDataError, match="change of status is not allowed"):
        site_data.owner_update(s, "appointments", row, {"status": "New"})
    with pytest.raises(SiteDataError, match="Only the status"):
        site_data.owner_update(s, "appointments", row, {"phone": "0300 2222222"})


def test_the_owner_keeps_their_own_lists(site):
    s = site["storage"]
    added = site_data.owner_add(s, "stylists", {"name": "Sara Ahmed", "role": "Senior stylist"})["id"]
    site_data.owner_update(s, "stylists", added, {"role": "Colour specialist"})
    assert "Sara Ahmed" in [r["name"] for r in site_data.list_public(s, "stylists")]
    site_data.owner_delete(s, "stylists", added)
    with pytest.raises(SiteDataError, match="Please fill in 'Name'"):
        site_data.owner_add(s, "stylists", {"role": "x"})
    used = site_data.list_public(s, "stylists")[0]["id"]
    _ = _booking(s)                                                       # the first stylist now has a booking
    with pytest.raises(SiteDataError, match="still used"):
        site_data.owner_delete(s, "stylists", used)
    with pytest.raises(SiteDataError, match="cannot be deleted"):
        site_data.owner_delete(s, "appointments", site_data.owner_rows(s, "appointments")["rows"][0]["id"])


def test_sample_rows_go_and_real_ones_stay(site):
    s = site["storage"]
    stylist = site_data.owner_add(s, "stylists", {"name": "Real Stylist"})["id"]
    service = site_data.owner_add(s, "services", {"name": "Real Cut", "duration": 45})["id"]
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute(f'INSERT INTO "{s.schema}"."working_hours" (day, opens, closes) VALUES (%s, %s, %s)',
                     ("Monday", time(9), time(18)))
    assert site_data.clear_samples(s)["removed"] > 0
    names = [r["name"] for r in site_data.list_public(s, "stylists")]
    assert names == ["Real Stylist"] and site_data.owner_rows(s, "appointments")["rows"] == []
    assert [r["id"] for r in site_data.list_public(s, "services")] == [service] and stylist


def test_only_the_owner_reaches_the_dashboard(site):
    async def scenario():
        engine = new_engine()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_session] = session_dependency(engine)
        who = {"id": site["user"]}
        app.dependency_overrides[get_verified_user_id] = lambda: who["id"]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            mine = await client.get(f"/api/projects/{site['project']}/data")
            who["id"] = uuid.uuid4()
            theirs = await client.get(f"/api/projects/{site['project']}/data")
        await engine.dispose()
        return mine, theirs

    mine, theirs = asyncio.run(scenario())
    assert mine.status_code == 200 and {t["name"] for t in mine.json()["tables"]} >= {"appointments", "stylists"}
    assert theirs.status_code == 404 and "keeps no data" in theirs.json()["message"]


def test_sample_rows_in_use_stay_and_the_rest_go(site):
    s = site["storage"]
    _booking(s)                                                           # a real booking with a sample stylist
    result = site_data.clear_samples(s)
    assert result["removed"] > 0 and result["kept"] == 2                  # its sample service and stylist
    rows = site_data.owner_rows(s, "appointments")["rows"]
    assert [r["client_name"] for r in rows] == ["Sara"]
