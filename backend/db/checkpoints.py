# D:\FYP\FORGE-1\backend\db\checkpoints.py
"""
Where paused and stopped runs are saved (persistence plan). LangGraph writes a checkpoint after every step,
including the steps inside each agent's subgraph, into PostgreSQL next to the rest of the project data,
so a run survives a crash, a restart or a redeploy and can be continued from its last saved step.

psycopg cannot use Windows' default ProactorEventLoop; backend/main.py starts uvicorn on a SelectorEventLoop.
Prepared statements are switched off so the same URL works through Supabase's session and transaction poolers.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.engine import make_url

from agents.state import msgpack_allowlist


def libpq_url(url: str) -> str:
    """A SQLAlchemy URL (postgresql+asyncpg://...?pgbouncer=true) as the plain URL psycopg expects."""
    return make_url(url).set(drivername="postgresql", query={}).render_as_string(hide_password=False)


@asynccontextmanager
async def open_checkpointer(url: str, max_connections: int = 5) -> AsyncIterator[AsyncPostgresSaver]:
    kwargs = {"autocommit": True, "prepare_threshold": None, "row_factory": dict_row}
    try:   # fail fast with the real reason (wrong password, unknown host) instead of a 30-second pool timeout
        await (await AsyncConnection.connect(libpq_url(url), connect_timeout=15)).close()
    except psycopg.OperationalError as error:
        reason = str(error).strip().splitlines()[-1]
        raise RuntimeError(f"Cannot connect to the database in SUPABASE_DB_URL: {reason}") from None
    async with AsyncConnectionPool(libpq_url(url), kwargs=kwargs, max_size=max_connections, open=False) as pool:
        saver = AsyncPostgresSaver(pool, serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist()))
        await saver.setup()          # creates the checkpoint tables once; safe to repeat
        yield saver
