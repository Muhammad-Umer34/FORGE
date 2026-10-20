# D:\FYP\FORGE-1\backend\services\limits.py
"""
Rate limits and daily caps (D-189), stored in PostgreSQL so they hold across server restarts and
processes. Each limit is a counter per key per fixed time window ("this address, this hour").

`count_hit` adds one and reads the new total in a single statement, so simultaneous requests are
counted exactly. Functions marked "in a transaction" use the caller's open transaction; the
others open and commit their own.
"""
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


class RateLimited(Exception):
    def __init__(self, retry_after_s: int):
        super().__init__(retry_after_s)
        self.retry_after_s = max(1, retry_after_s)


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime


def window_for(length: timedelta, now: datetime | None = None) -> Window:
    now = now or datetime.now(timezone.utc)
    index = (now - _EPOCH) // length
    start = _EPOCH + index * length
    return Window(start, start + length)


def _retry_after(window: Window) -> int:
    return int((window.end - datetime.now(timezone.utc)).total_seconds()) + 1


async def count_hit(session: AsyncSession | AsyncConnection, key: str, length: timedelta) -> int:
    """In a transaction: add one to this window's counter and return the new count."""
    window = window_for(length)
    total = await session.scalar(text(
        "INSERT INTO rate_limits (key, window_start, count) VALUES (:key, :start, 1) "
        "ON CONFLICT (key, window_start) DO UPDATE SET count = rate_limits.count + 1 RETURNING count"
    ), {"key": key, "start": window.start})
    if random.random() < 0.01:  # now and then, drop windows that ended long ago
        await session.execute(text("DELETE FROM rate_limits WHERE window_start < :old"),
                              {"old": datetime.now(timezone.utc) - 2 * DAY})
    return total


async def current(session: AsyncSession, key: str, length: timedelta) -> int:
    """In a transaction: this window's count, without adding to it."""
    window = window_for(length)
    value = await session.scalar(text("SELECT count FROM rate_limits WHERE key = :key AND window_start = :start"),
                                 {"key": key, "start": window.start})
    return value or 0


async def clear(session: AsyncSession, key: str) -> None:
    """In a transaction: forget a key in every window (e.g. after a successful sign-in)."""
    await session.execute(text("DELETE FROM rate_limits WHERE key = :key"), {"key": key})


def retry_after(length: timedelta) -> int:
    return _retry_after(window_for(length))


async def take(session: AsyncSession, *rules: tuple[str, int, timedelta]) -> None:
    """Use one unit of each (key, limit, window) rule, all or nothing. Raises RateLimited, using
    nothing, when any rule is already full. Counts on a separate connection of the same database, so
    rolling back a full rule never expires objects the caller's session has loaded."""
    async with session.bind.connect() as conn, conn.begin():
        for key, limit, length in rules:
            if await count_hit(conn, key, length) > limit:
                raise RateLimited(_retry_after(window_for(length)))  # leaving the block rolls back every count


async def try_take(session: AsyncSession, key: str, limit: int, length: timedelta) -> bool:
    """Like `take` for one rule, but answers True/False instead of raising."""
    try:
        await take(session, (key, limit, length))
        return True
    except RateLimited:
        return False
