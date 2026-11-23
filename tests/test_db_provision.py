"""A site's own storage (D-243) and the Database Agent's build step, on the local PostgreSQL."""
import uuid

import psycopg
import pytest

from agents.database_generator import agent as database_agent
from agents.database_generator import provision
from agents.file_store import MemoryFileStore
from agents.planning import data_patterns as dp
from agents.state import BuildPlan, RunConfig
from backend.core.config import settings
from pg_support import requires_db


def _url() -> str:
    return provision.plain_url(settings.TEST_DATABASE_URL or "")


def _salon() -> BuildPlan:
    entities, _ = dp.expand([{"pattern": "appointments", "names": {"staff": "stylists"}}])
    return BuildPlan(data_entities=entities)


@pytest.fixture
def store(monkeypatch):
    s = MemoryFileStore()
    monkeypatch.setattr(database_agent, "active_store", lambda: s)
    return s


def test_names_are_safe_for_any_project_id():
    assert provision.schema_for("8b1c0d2e-0000-4000-8000-000000000000") == "site_8b1c0d2e0000"
    assert provision.schema_for("test").startswith("site_") and provision.role_for("site_x") == "site_x_role"


def test_a_site_that_stores_nothing_skips_the_agent(store):
    lines = []
    out = database_agent.run(BuildPlan(), "req_1", "test", RunConfig(), lines.append)
    assert out.status == "done" and out.files == [] and "No data to store" in lines[0]["message"]


def test_with_storage_off_the_files_are_still_written(store):
    lines = []
    out = database_agent.run(_salon(), "req_2", "test", RunConfig(database=False), lines.append)
    assert {f.path for f in out.files} == {"db/schema.sql", "db/schema.json", "db/er.mmd", "db/seed.sql"}
    assert all(f.kind == "database" and f.written_by == "code" for f in out.files)
    assert "CREATE TABLE" in store.read("req_2")["db/schema.sql"]


@requires_db
def test_build_step_gates_then_provisions_a_private_schema(store):
    project = str(uuid.uuid4())
    schema = provision.schema_for(project)
    lines, report = [], {}
    try:
        out = database_agent.run(_salon(), "req_3", project, RunConfig(database=True), lines.append, url=_url(),
                                 report=report)
        messages = [x["message"] for x in lines]
        assert out.status == "done" and "Database: site storage ready" in messages
        assert report["db_gate"] and report["db_tests"] == report["db_tests_passed"] == 7
        with psycopg.connect(_url()) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s", (schema,))}
            assert {"appointments", "stylists", "services", "working_hours", "days_off"} <= tables
            assert conn.execute(f'SELECT count(*) FROM "{schema}"."appointments" WHERE is_sample').fetchone()[0] == 3
    finally:
        provision.drop(_url(), project)


@requires_db
def test_the_site_role_reaches_only_its_own_schema():
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    try:
        made_a = provision.provision(_salon().data_entities, _url(), a)
        made_b = provision.provision(_salon().data_entities, _url(), b)
        with psycopg.connect(_url()) as conn:
            with conn.transaction():
                conn.execute(f'SET LOCAL ROLE "{made_a["role"]}"')
                assert conn.execute(f'SELECT count(*) FROM "{made_a["schema"]}"."services"').fetchone()[0] == 3
            with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
                conn.execute(f'SET LOCAL ROLE "{made_a["role"]}"')
                conn.execute(f'SELECT count(*) FROM "{made_b["schema"]}"."services"')
            with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
                conn.execute(f'SET LOCAL ROLE "{made_a["role"]}"')
                conn.execute(f'DELETE FROM "{made_a["schema"]}"."appointments"')      # no deletes for a site
    finally:
        provision.drop(_url(), a)
        provision.drop(_url(), b)


@requires_db
def test_a_rebuild_keeps_real_data_and_replaces_samples():
    project = str(uuid.uuid4())
    schema = provision.schema_for(project)
    entities = _salon().data_entities
    kept = None
    try:
        assert provision.provision(entities, _url(), project)["kept_old_schema"] is None
        assert provision.provision(entities, _url(), project)["kept_old_schema"] is None   # only samples: replaced
        with psycopg.connect(_url(), autocommit=True) as conn:
            conn.execute(f'UPDATE "{schema}"."services" SET is_sample = false WHERE name LIKE %s', ("Sample%1",))
        kept = provision.provision(entities, _url(), project)["kept_old_schema"]
        assert kept and kept.startswith(f"{schema}_old_")
        with psycopg.connect(_url()) as conn:
            assert conn.execute(f'SELECT count(*) FROM "{kept}"."services" WHERE NOT is_sample').fetchone()[0] == 1
    finally:
        provision.drop(_url(), project)
        if kept:
            with psycopg.connect(_url(), autocommit=True) as conn:
                conn.execute(f'DROP SCHEMA IF EXISTS "{kept}" CASCADE')


def test_a_plan_from_before_recipes_skips_storage_without_crashing(store):
    from agents.state import DataEntity, DataField
    old = BuildPlan(data_entities=[DataEntity(name="booking_requests", fields=[DataField(name="status", type="choice")])])
    lines = []
    out = database_agent.run(old, "req_4", "test", RunConfig(database=True), lines.append)
    assert out.status == "failed" and "plan the site again" in lines[-1]["message"]
