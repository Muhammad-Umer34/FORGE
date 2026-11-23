"""The database gate on a real PostgreSQL (D-245): every recipe, every switch combination, every rule proved."""
import itertools
import threading
import uuid

import psycopg
import pytest

from agents.database_generator.compile import compile_schema
from agents.database_generator.gate import run_gate
from agents.database_generator.seed import seed_rows, seed_sql
from agents.planning import data_patterns as dp
from backend.core.config import settings
from pg_support import requires_db

pytestmark = requires_db


def _url() -> str:
    url = settings.TEST_DATABASE_URL or ""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")


def _combos(recipe):
    ids = [s["id"] for s in recipe["switches"]]
    for values in itertools.product(*[[o["value"] for o in s["options"]] for s in recipe["switches"]]):
        yield dict(zip(ids, values))


@pytest.mark.parametrize("pattern_id", sorted(dp.load()))
def test_every_rule_of_every_recipe_holds_in_postgres(pattern_id):
    for n, switches in enumerate(_combos(dp.load()[pattern_id])):
        entities, _ = dp.expand([{"pattern": pattern_id, "switches": switches}])
        result, _ = run_gate(entities, _url(), f"test-{pattern_id}-{n}")
        assert result.ok, (switches, result.message, [t for t in result.tests if not t["ok"]])
        assert len(result.tests) == sum(1 for e in entities for r in e.rules if r.enabled)


def test_nothing_stays_after_the_gate():
    entities, _ = dp.expand([{"pattern": "appointments"}])
    run_gate(entities, _url(), "test-cleanup")
    with psycopg.connect(_url()) as conn:
        left = conn.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'check_%'").fetchall()
    assert left == []


def test_without_btree_gist_the_trigger_version_also_holds(monkeypatch):
    import agents.database_generator.gate as gate
    real = gate.compile_schema
    monkeypatch.setattr(gate, "compile_schema", lambda e, s, tz, gist: real(e, s, tz, gist=False))
    for pattern_id in ("appointments", "rentals"):
        entities, _ = dp.expand([{"pattern": pattern_id}])
        result, compiled = gate.run_gate(entities, _url(), f"test-nogist-{pattern_id}")
        assert "EXCLUDE" not in compiled.schema_sql and result.ok, result.message


def test_two_people_cannot_take_the_last_place_together():
    """The capacity trigger locks the class time: of two bookings sent at once for the last place, one is waitlisted."""
    entities, _ = dp.expand([{"pattern": "classes", "switches": {"seats": "10"}}])
    schema = f"check_{uuid.uuid4().hex[:12]}"
    rows = seed_rows(entities)
    session_id = rows["sessions"][0]["id"]
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute(compile_schema(entities, schema).schema_sql)
        conn.execute(seed_sql(entities, schema))
        used = conn.execute(f'SELECT count(*) FROM "{schema}"."registrations" WHERE session_id = %s', (session_id,)).fetchone()[0]
        conn.execute(f'UPDATE "{schema}"."sessions" SET capacity = %s WHERE id = %s', (used + 1, session_id))
    try:
        statuses, start = [], threading.Barrier(2)

        def book(n):
            with psycopg.connect(_url()) as c:
                start.wait()
                row = c.execute(f'INSERT INTO "{schema}"."registrations" (name, email, session_id) '
                                f"VALUES (%s, %s, %s) RETURNING status", (f"P{n}", f"p{n}@example.com", session_id)).fetchone()
                statuses.append(row[0])

        threads = [threading.Thread(target=book, args=(n,)) for n in (1, 2)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert sorted(statuses) == ["Registered", "Waitlist"]
    finally:
        with psycopg.connect(_url(), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA "{schema}" CASCADE')
