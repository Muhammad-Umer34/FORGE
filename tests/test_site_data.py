"""The site data API (D-247) on the local PostgreSQL: a site key reaches only its own data, every value is checked
against the site's contract, rules come back as plain messages, and public lists never show personal data."""
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
from backend.db.session import get_session
from backend.routes.site_data import router
from backend.services import site_data
from backend.services.site_data import SiteDataError, Storage
from pg_support import migrate_test_database, new_engine, requires_db, session_dependency

pytestmark = requires_db
TZ = ZoneInfo("Asia/Karachi")


def _url() -> str:
    return provision.plain_url(settings.TEST_DATABASE_URL or "")


@pytest.fixture(scope="module")
def site():
    """A salon with stylists, provisioned and registered for a real project; dropped afterwards."""
    migrate_test_database()
    site_data.use_pool(None)
    site_data.pool(_url())
    with psycopg.connect(_url(), autocommit=True) as conn:
        user = conn.execute("INSERT INTO users (email, password_hash, display_name) VALUES (%s, 'x', 'T') RETURNING id",
                            (f"t{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]
        project = str(conn.execute("INSERT INTO projects (owner_id, name) VALUES (%s, 'Salon') RETURNING id",
                                   (user,)).fetchone()[0])
    entities, _ = dp.expand([{"pattern": "appointments", "names": {"staff": "stylists"}},
                             {"pattern": "orders"}, {"pattern": "classes", "switches": {"seats": "10"}}])
    made = provision.provision(entities, _url(), project)
    key = provision.register(_url(), project, made, "req_test")
    storage = Storage(project, made["schema"], made["role"], made["contract"])
    yield {"project": project, "key": key, "storage": storage, "user": user}
    provision.drop(_url(), project)
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))
    site_data.pool().close()
    site_data.use_pool(None)


def _ids(storage, table):
    return [r["id"] for r in site_data.list_public(storage, table)]


def _slot(days: int, hour: int) -> str:
    day = datetime.now(TZ).date() + timedelta(days=days)
    while day.weekday() == 6:                      # the sample hours are Monday to Saturday
        day += timedelta(days=1)
    return datetime.combine(day, time(hour, 0), TZ).isoformat()


def _booking(storage, **change):
    payload = {"client_name": "Ayesha", "phone": "0300 1234567", "service_id": _ids(storage, "services")[0],
               "staff_id": _ids(storage, "stylists")[0], "start_at": _slot(5, 15)}
    return {**payload, **change}


def test_registry_holds_only_the_key_hash(site):
    with psycopg.connect(_url()) as conn:
        row = conn.execute("SELECT preview_key_hash, schema_name FROM site_storage WHERE project_id = %s",
                           (site["project"],)).fetchone()
    assert row[0] and row[0] != site["key"] and len(row[0]) == 64 and row[1] == site["storage"].schema


def test_a_booking_is_saved_as_new_and_a_double_booking_gets_a_plain_message(site):
    s = site["storage"]
    saved = site_data.submit(s, "appointments", _booking(s, start_at=_slot(6, 11), status="Done", end_at="x"))
    assert saved["status"] == "New"                               # a visitor cannot set the status
    with pytest.raises(SiteDataError, match="That time is already taken") as refused:
        site_data.submit(s, "appointments", _booking(s, client_name="Bilal", start_at=_slot(6, 11)))
    assert refused.value.status == 409


@pytest.mark.parametrize("change, says, field", [
    ({"phone": None}, "Please fill in 'Phone'", "phone"),
    ({"phone": "call me maybe"}, "Please check 'Phone'", "phone"),
    ({"email": "not-an-email"}, "an email address", "email"),
    ({"service_id": "nope"}, "Please choose a valid service", "service_id"),
    ({"start_at": "tomorrow"}, "a date and time", "start_at"),
    ({"hair_colour": "red"}, "does not keep", "hair_colour"),
])
def test_values_are_checked_against_the_contract(site, change, says, field):
    with pytest.raises(SiteDataError, match=says) as refused:
        site_data.submit(site["storage"], "appointments", _booking(site["storage"], **change))
    assert refused.value.field == field and refused.value.status == 422


def test_rules_come_back_in_plain_words(site):
    s = site["storage"]
    with pytest.raises(SiteDataError, match="at least 2 hours ahead"):
        site_data.submit(s, "appointments", _booking(s, start_at=(datetime.now(TZ) + timedelta(minutes=20)).isoformat()))
    sunday = datetime.now(TZ).date() + timedelta(days=(6 - datetime.now(TZ).weekday()) % 7 + 7)
    with pytest.raises(SiteDataError, match="closed at that time"):
        site_data.submit(s, "appointments", _booking(s, start_at=datetime.combine(sunday, time(11), TZ).isoformat()))


def test_an_order_and_its_items_are_saved_together_or_not_at_all(site):
    s = site["storage"]
    items = _ids(s, "catalogue_items")
    order = {"customer_name": "Sana", "phone": "0300 7654321", "fulfilment": "Pickup", "needed_at": _slot(4, 12)}
    saved = site_data.submit(s, "orders", {**order, "items": [{"item_id": items[0], "quantity": 2},
                                                             {"item_id": items[1], "quantity": 1}]})
    with psycopg.connect(_url()) as conn:
        count = conn.execute(f'SELECT count(*) FROM "{s.schema}"."order_items" WHERE order_id = %s',
                             (saved["id"],)).fetchone()[0]
    assert count == 2
    with pytest.raises(SiteDataError, match="Quantity"):
        site_data.submit(s, "orders", {**order, "items": [{"item_id": items[0], "quantity": 0}]})
    with pytest.raises(SiteDataError, match="This site does not take that form"):
        site_data.submit(s, "order_items", {"item_id": items[0], "quantity": 1})   # only through its order


def test_a_full_class_puts_people_on_the_waitlist(site):
    s = site["storage"]
    session = _ids(s, "sessions")[0]
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute(f'UPDATE "{s.schema}"."sessions" SET capacity = 1 WHERE id = %s', (session,))
    saved = site_data.submit(s, "registrations", {"name": "Hira", "email": "hira@example.com", "session_id": session})
    assert saved["status"] == "Waitlist" and "waitlist" in saved["message"]


def test_public_lists_never_show_personal_data_or_submissions(site):
    s = site["storage"]
    services = site_data.list_public(s, "services")
    assert services and {"id", "name", "duration", "price"} <= set(services[0])
    with pytest.raises(SiteDataError, match="no such list"):
        site_data.list_public(s, "appointments")
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute(f'UPDATE "{s.schema}"."catalogue_items" SET available = false WHERE id = %s',
                     (_ids(s, "catalogue_items")[0],))
    assert len(_ids(s, "catalogue_items")) == 2                    # a hidden item is not listed


def test_the_routes_need_the_right_key(site):
    async def scenario():
        engine = new_engine()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_session] = session_dependency(engine)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            no_key = await client.get("/api/site-data/services")
            wrong = await client.get("/api/site-data/services", headers={"X-Forge-Site-Key": "fsk_wrong"})
            listed = await client.get("/api/site-data/services", headers={"X-Forge-Site-Key": site["key"]})
            booked = await client.post("/api/site-data/appointments", headers={"X-Forge-Site-Key": site["key"]},
                                       json=_booking(site["storage"], start_at=_slot(7, 16)))
            again = await client.post("/api/site-data/appointments", headers={"X-Forge-Site-Key": site["key"]},
                                      json=_booking(site["storage"], start_at=_slot(7, 16)))
            missing = await client.post("/api/site-data/appointments", headers={"X-Forge-Site-Key": site["key"]},
                                        json={"client_name": "X"})
        await engine.dispose()
        return no_key, wrong, listed, booked, again, missing

    no_key, wrong, listed, booked, again, missing = asyncio.run(scenario())
    assert no_key.status_code == wrong.status_code == 401
    assert "not connected" in wrong.json()["message"]
    assert listed.status_code == 200 and len(listed.json()["rows"]) >= 3
    assert booked.status_code == 201 and booked.json()["status"] == "New"
    assert again.status_code == 409 and again.json() == {"ok": False, "message": "That time is already taken. Please pick another.",
                                                         "field": None}
    assert missing.status_code == 422 and missing.json()["field"] == "phone"


def test_a_key_reaches_only_its_own_site(site):
    other = str(uuid.uuid4())
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("INSERT INTO projects (id, owner_id, name) VALUES (%s, %s, 'Other')", (other, site["user"]))
    entities, _ = dp.expand([{"pattern": "contact"}])
    made = provision.provision(entities, _url(), other)
    try:
        theirs = Storage(other, made["schema"], made["role"], made["contract"])
        with pytest.raises(SiteDataError, match="does not take that form"):
            site_data.submit(theirs, "appointments", _booking(site["storage"]))
        forged = Storage(other, site["storage"].schema, made["role"], site["storage"].contract)   # wrong role
        with pytest.raises(SiteDataError):
            site_data.submit(forged, "appointments", _booking(site["storage"], start_at=_slot(8, 10)))
    finally:
        provision.drop(_url(), other)


def test_free_times_skip_bookings_closed_days_and_the_notice(site):
    s = site["storage"]
    stylist, service = _ids(s, "stylists")[1], _ids(s, "services")[0]
    day = datetime.fromisoformat(_slot(9, 10)).date()
    free = site_data.availability(s, "appointments", day.isoformat(), {"staff_id": stylist, "service_id": service})
    assert free[0] == "09:00" and free[-1] == "17:30"           # sample hours 09:00-18:00, 30-minute service
    site_data.submit(s, "appointments", _booking(s, staff_id=stylist, start_at=datetime.combine(day, time(11), TZ).isoformat()))
    after = site_data.availability(s, "appointments", day.isoformat(), {"staff_id": stylist, "service_id": service})
    assert "11:00" not in after and "10:30" in after and "11:30" in after
    other = site_data.availability(s, "appointments", day.isoformat(), {"staff_id": _ids(s, "stylists")[2]})
    assert "11:00" in other                                       # another stylist is still free
    sunday = day + timedelta(days=(6 - day.weekday()) % 7)
    assert site_data.availability(s, "appointments", sunday.isoformat(), {"staff_id": stylist}) == []
    today = datetime.now(TZ)
    soon = site_data.availability(s, "appointments", today.date().isoformat(), {"staff_id": stylist})
    assert all(datetime.combine(today.date(), time.fromisoformat(t), TZ) >= today + timedelta(hours=2) for t in soon)
    with pytest.raises(SiteDataError, match="no times"):
        site_data.availability(s, "orders", day.isoformat(), {})


def test_the_per_site_rate_limit_counts_in_memory():
    from backend.routes import site_data as routes
    s = Storage("p-limit", "site_x", "site_x_role", {"tables": []})
    routes._hits.clear()
    assert all(routes._limited(s, "write", 3) is None for _ in range(3))
    refused = routes._limited(s, "write", 3)
    assert refused.status_code == 429
    assert routes._limited(Storage("other", "s", "r", {}), "write", 3) is None      # per site
