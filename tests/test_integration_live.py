"""The Integration Agent's live check (D-254) end to end, with nothing faked: a salon's storage on the test database,
FORGE's site-data API on a real port, and the site itself running in a real Next.js preview whose own routes forward
to it. A booking goes through the site, the same time is refused by the database, a missing field by the site's zod
check, and no test row is left behind. Slow (~30 s: the dev server compiles its routes)."""
import json
import socket
import threading
import time
import uuid

import psycopg
import pytest
import uvicorn
from fastapi import FastAPI

from agents import build_worker, preview
from agents.backend_generator.agent import contract_json, form_specs, schemas_ts
from agents.backend_generator.gate import sample_payload
from agents.database_generator import provision
from agents.database_generator.seed import seed_rows
from agents.frontend_generator.compiler import compile_site
from agents.integration.live import check_live
from backend.core.config import settings
from backend.db.session import get_session
from backend.routes import site_data as site_routes
from backend.services import site_data
from pg_support import migrate_test_database, new_engine, requires_db, session_dependency
from test_backend_agent import salon_plan

pytestmark = [requires_db, pytest.mark.skipif(not (build_worker.TEMPLATE / "node_modules" / "next").is_dir(),
                                              reason="the site template's node_modules are not installed")]


def _url() -> str:
    return provision.plain_url(settings.TEST_DATABASE_URL or "")


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def forge_api(monkeypatch):
    """FORGE's site-data routes on a real port, reading keys from the test database."""
    app = FastAPI()
    app.include_router(site_routes.router)
    engine = new_engine()
    app.dependency_overrides[get_session] = session_dependency(engine)
    port = _port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                                           loop="asyncio:SelectorEventLoop"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    monkeypatch.setattr(settings, "FORGE_API_URL", f"http://127.0.0.1:{port}")
    yield
    server.should_exit = True
    thread.join(10)


@pytest.fixture
def salon(forge_api):
    migrate_test_database()
    site_data.use_pool(None)
    site_data.pool(_url())
    site_routes._known.clear()
    site_routes._hits.clear()
    with psycopg.connect(_url(), autocommit=True) as conn:
        user = conn.execute("INSERT INTO users (email, password_hash, display_name) VALUES (%s, 'x', 'L') RETURNING id",
                            (f"l{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]
        project = str(conn.execute("INSERT INTO projects (owner_id, name) VALUES (%s, 'Salon') RETURNING id",
                                   (user,)).fetchone()[0])
    plan = salon_plan()
    made = provision.provision(plan.data_entities, _url(), project)
    request_id = f"req_live_{uuid.uuid4().hex[:6]}"
    preview.set_site_key(request_id, provision.register(_url(), project, made, request_id))
    specs = form_specs(plan)
    files = {**compile_site(plan, "hair salon", request_id), "lib/forms.json": json.dumps(specs),
             "lib/schemas.ts": schemas_ts(specs), "api/contract.json": contract_json(plan, specs)}
    live = preview.start(request_id, files)
    yield {"plan": plan, "made": made, "url": live.url, "specs": specs}
    preview.stop_all()
    provision.drop(_url(), project)
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))
    site_data.pool().close()
    site_data.use_pool(None)


def test_a_booking_goes_through_the_site_and_is_removed_again(salon):
    plan, made = salon["plan"], salon["made"]
    rows = seed_rows(plan.data_entities, "Asia/Karachi")
    tables = {t["name"]: t for t in made["contract"]["tables"]}
    result = check_live(salon["url"], salon["specs"], tables, made["schema"], _url(),
                        lambda spec: sample_payload(spec, rows, plan))
    steps = {what: (ok, detail) for what, ok, detail in result.steps}
    assert result.ok, result.steps
    assert steps["Appointments: a submission through the site is saved"][1].startswith("201")
    assert "already taken" in steps["Appointments: the same time again is refused by the database"][1]
    assert result.saved == 1 and steps["test rows removed"] == (True, "1 removed")
    with psycopg.connect(_url()) as conn:
        left = conn.execute(f'SELECT count(*) FROM "{made["schema"]}"."appointments" WHERE client_name = %s',
                            ("FORGE test",)).fetchone()[0]
    assert left == 0


def test_a_missing_field_is_refused_by_the_sites_own_check(salon):
    """The check the live step uses for forms without a no-overlap rule, tried on the booking form's own route."""
    import httpx
    spec = next(iter(salon["specs"].values()))
    payload = sample_payload(spec, seed_rows(salon["plan"].data_entities, "Asia/Karachi"), salon["plan"])
    payload.pop("phone")
    with httpx.Client(base_url=salon["url"], timeout=60) as client:
        reply = client.post(f"/api/data/{spec['table']}", json=payload)
    assert reply.status_code == 422 and reply.json()["field"] == "phone"
