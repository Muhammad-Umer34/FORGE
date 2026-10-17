# D:\FYP\FORGE-1\backend\db\session.py
"""
Database connection for the API layer (D-172). Agents never touch the database (D-133);
routes get a session through `get_session` and pass it to a service in `backend/services/`.

Behind Supabase's transaction pooler a client may land on a different server connection for every
transaction, so there asyncpg's prepared-statement caches are switched off and statement names made
unique. On a direct or session-pooler connection the caches stay on: each query then costs one
network round trip instead of two.
"""
from collections.abc import AsyncIterator
from functools import lru_cache
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings


def _transaction_pooler(url) -> bool:
    """Supabase's transaction pooler (port 6543, or a URL marked pgbouncer=true) can't keep prepared statements."""
    return url.port == 6543 or "pgbouncer" in url.query


def make_engine(url: str, **kwargs) -> AsyncEngine:
    """Async engine for a postgres:// or postgresql+asyncpg:// URL. Prepared-statement caching is
    switched off only behind a transaction pooler; elsewhere it saves a network round trip per query."""
    sa_url = make_url(url).set(drivername="postgresql+asyncpg")
    connect_args = {}
    if _transaction_pooler(sa_url):
        sa_url = sa_url.update_query_dict({"prepared_statement_cache_size": "0"})
        connect_args = {"statement_cache_size": 0, "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"}
    # Supabase's copy-paste URLs may carry Prisma's "pgbouncer=true"; asyncpg rejects it.
    sa_url = sa_url.difference_update_query(["pgbouncer"])
    return create_async_engine(sa_url, pool_pre_ping=True, connect_args=connect_args, **kwargs)


def sqlstate(error: DBAPIError) -> str | None:
    """PostgreSQL's 5-character error code behind a SQLAlchemy error (e.g. 23505 = duplicate)."""
    return getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@lru_cache(maxsize=1)
def _app_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return make_sessionmaker(make_engine(settings.SUPABASE_DB_URL))


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per HTTP request, always closed afterwards."""
    if not settings.SUPABASE_DB_URL:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The database is not configured.")
    async with _app_sessionmaker()() as session:
        yield session
