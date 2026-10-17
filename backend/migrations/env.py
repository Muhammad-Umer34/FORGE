# D:\FYP\FORGE-1\backend\migrations\env.py
"""Runs migrations online against PostgreSQL with the same pooler-safe engine as the app (D-173)."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.pool import NullPool

from backend.core.config import settings
from backend.db.session import make_engine
from backend.db.tables import Base

config = context.config
if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    url = config.attributes.get("url") or (
        settings.TEST_DATABASE_URL if context.get_x_argument(as_dictionary=True).get("db") == "test"
        else settings.SUPABASE_DB_URL
    )
    if not url:
        raise RuntimeError("No database URL: set SUPABASE_DB_URL (or TEST_DATABASE_URL with -x db=test) in .env")
    return url


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _main() -> None:
    engine = make_engine(_url(), poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline (SQL script) mode is not used in FORGE; run migrations against a database.")
asyncio.run(_main())
