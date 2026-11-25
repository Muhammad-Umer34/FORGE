# D:\FYP\FORGE-1\backend\routes\site_data.py
"""
The site data API (D-247): a few fixed routes that every generated site's server calls with its secret key, whatever
the site keeps. The key says which project; the project's contract says which tables and fields exist. Answers are
{"ok": true, ...} or {"ok": false, "message", "field"} with the HTTP status, so the site can show the message as is.
"""
import asyncio
import hashlib
import logging
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.session import get_session
from backend.db.tables import SiteStorage
from backend.services.site_data import SiteDataError, Storage, availability, list_public, submit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/site-data", tags=["Site data"])
WINDOW = timedelta(minutes=10)


def _answer(http_status: int, **body) -> JSONResponse:
    return JSONResponse(status_code=http_status, content=body)


def _refused(error: SiteDataError) -> JSONResponse:
    return _answer(error.status, ok=False, message=error.message, field=error.field)


async def _storage(session: AsyncSession, key: str | None) -> Storage | None:
    if not key or len(key) > 200:
        return None
    digest = hashlib.sha256(key.encode()).hexdigest()
    cached = _known.get(digest)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    row = await session.scalar(select(SiteStorage).where(
        or_(SiteStorage.key_hash == digest, SiteStorage.preview_key_hash == digest)))
    storage = Storage(str(row.project_id), row.schema_name, row.role_name, row.contract) if row else None
    if storage:                                          # unknown keys are not cached: a new build's key works at once
        _known[digest] = (time.monotonic() + KEY_CACHE_SECONDS, storage)
    return storage


# Live (journal #34): a new connection to FORGE's database took about 7 s, so a key lookup and a rate-limit count per
# request could pass the site's 10 s timeout. Keys are remembered for a minute; rate limits are counted in memory.
# shortcut: in-memory, so per server process; move to a shared store when FORGE runs on several servers.
KEY_CACHE_SECONDS = 60
_known: dict[str, tuple[float, Storage]] = {}
_hits: dict[str, deque] = defaultdict(deque)


def _limited(storage: Storage, kind: str, limit: int) -> JSONResponse | None:
    now, window = time.monotonic(), WINDOW.total_seconds()
    hits = _hits[f"{kind}:{storage.project_id}"]
    while hits and hits[0] <= now - window:
        hits.popleft()
    if len(hits) >= limit:
        return _answer(429, ok=False, message="Too many requests right now. Please try again in a few minutes.")
    hits.append(now)
    return None


_NO_KEY = SiteDataError(401, "This site is not connected to FORGE.")


@router.post("/{table}")
async def post_row(table: str, request: Request, x_forge_site_key: str | None = Header(default=None),
                   session: AsyncSession = Depends(get_session)):
    """Save what a visitor sent (a booking, a message, an order with its items)."""
    storage = await _storage(session, x_forge_site_key)
    if not storage:
        return _refused(_NO_KEY)
    if busy := _limited(storage, "write", settings.LIMIT_SITE_WRITES_PER_10MIN):
        return busy
    try:
        payload = await request.json()
    except ValueError:
        return _refused(SiteDataError(422, "The form could not be read. Please try again."))
    try:
        saved = await asyncio.to_thread(submit, storage, table, payload)
    except SiteDataError as error:
        if error.status >= 500:
            logger.error("Site data: %s %s failed: %s", storage.project_id, table, error.__cause__)
        return _refused(error)
    return _answer(201, ok=True, **saved)


@router.get("/{table}/availability")
async def get_free_times(table: str, request: Request, x_forge_site_key: str | None = Header(default=None),
                         session: AsyncSession = Depends(get_session)):
    """Free start times on ?date=YYYY-MM-DD for a booking form; the visitor's picks (e.g. ?staff_id=, ?service_id=)
    narrow them."""
    storage = await _storage(session, x_forge_site_key)
    if not storage:
        return _refused(_NO_KEY)
    if busy := _limited(storage, "read", settings.LIMIT_SITE_READS_PER_10MIN):
        return busy
    picks = {k: v for k, v in request.query_params.items() if k != "date"}
    try:
        times = await asyncio.to_thread(availability, storage, table, request.query_params.get("date", ""), picks)
    except SiteDataError as error:
        return _refused(error)
    return _answer(200, ok=True, times=times)


@router.get("/{table}")
async def get_rows(table: str, x_forge_site_key: str | None = Header(default=None),
                   session: AsyncSession = Depends(get_session)):
    """A public list the site shows or offers in a form (services, stylists, class times)."""
    storage = await _storage(session, x_forge_site_key)
    if not storage:
        return _refused(_NO_KEY)
    if busy := _limited(storage, "read", settings.LIMIT_SITE_READS_PER_10MIN):
        return busy
    try:
        return _answer(200, ok=True, rows=await asyncio.to_thread(list_public, storage, table))
    except SiteDataError as error:
        return _refused(error)
