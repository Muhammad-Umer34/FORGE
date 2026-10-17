"""
Shared helpers for the PostgreSQL integration tests (not a test file itself). The tests run only
when TEST_DATABASE_URL is set; each test creates its own rows and deletes them afterwards.
"""
import asyncio
import time

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from backend.core.config import ROOT_DIR, settings
from backend.db.session import make_engine, make_sessionmaker

MIGRATIONS = ROOT_DIR / "backend" / "migrations"
WAIT_FOR_LOCK_S = 30

requires_db = pytest.mark.skipif(not settings.TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")


def migrate_test_database() -> None:
    cfg = Config(str(MIGRATIONS / "alembic.ini"))
    cfg.attributes["url"] = settings.TEST_DATABASE_URL
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def new_engine():
    """One engine per test (each test runs its own event loop), no pooling between tests."""
    return make_engine(settings.TEST_DATABASE_URL, poolclass=NullPool)


def session_dependency(engine):
    """A replacement for backend.db.session.get_session that uses the test database."""
    maker = make_sessionmaker(engine)

    async def test_session():
        async with maker() as session:
            yield session

    return test_session


async def wait_for_lock_waiters(engine, count: int, statement: str) -> None:
    """Wait until `count` sessions are blocked on a lock while running SQL that contains `statement`."""
    deadline = time.monotonic() + WAIT_FOR_LOCK_S
    while time.monotonic() < deadline:
        async with engine.connect() as conn:
            waiting = await conn.scalar(text(
                "SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() "
                "AND datname = current_database() AND wait_event_type = 'Lock' AND query ILIKE :pattern"
            ), {"pattern": f"%{statement}%"})
        if waiting >= count:
            return
        await asyncio.sleep(0.1)
    raise AssertionError(f"expected {count} sessions waiting on the lock; saw fewer")


async def open_transactions(engine, table: str) -> int:
    """Sessions left 'idle in transaction' whose last statement touched `table`."""
    async with engine.connect() as conn:
        return await conn.scalar(text(
            "SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() "
            "AND datname = current_database() AND state LIKE 'idle in transaction%' AND query ILIKE :pattern"
        ), {"pattern": f"%{table}%"})
