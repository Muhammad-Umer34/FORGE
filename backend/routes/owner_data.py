# D:\FYP\FORGE-1\backend\routes\owner_data.py
"""
The owner's dashboard (D-250): a signed-in owner sees what visitors sent to their site, moves its status, and keeps
their own lists (services, stylists, opening hours). Only their own projects; everything runs through the site data
service, so the same checks and plain messages apply.
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.deps import get_verified_user_id
from backend.db.session import get_session
from backend.db.tables import Project, SiteStorage
from backend.services import site_data
from backend.services.site_data import SiteDataError, Storage

router = APIRouter(prefix="/api/projects/{project_id}/data", tags=["Site data (owner)"])
NO_STORAGE = SiteDataError(404, "This site keeps no data yet. It is set up when the site is built with storage on.")


async def owned_storage(project_id: uuid.UUID, user_id: uuid.UUID = Depends(get_verified_user_id),
                        session: AsyncSession = Depends(get_session)) -> Storage:
    row = await session.scalar(select(SiteStorage).join(Project, Project.id == SiteStorage.project_id)
                               .where(SiteStorage.project_id == project_id, Project.owner_id == user_id))
    if not row:
        raise NO_STORAGE
    return Storage(str(row.project_id), row.schema_name, row.role_name, row.contract)


def _refused(error: SiteDataError) -> JSONResponse:
    return JSONResponse(status_code=error.status, content={"ok": False, "message": error.message, "field": error.field})


async def _run(fn, *args) -> JSONResponse:
    try:
        return JSONResponse(content={"ok": True, **((await asyncio.to_thread(fn, *args)) or {})})
    except SiteDataError as error:
        return _refused(error)


async def _storage_or_refusal(project_id, user_id, session):
    try:
        return await owned_storage(project_id, user_id, session), None
    except SiteDataError as error:
        return None, _refused(error)


@router.get("")
async def lists(project_id: uuid.UUID, user_id: uuid.UUID = Depends(get_verified_user_id),
                session: AsyncSession = Depends(get_session)):
    storage, refused = await _storage_or_refusal(project_id, user_id, session)
    return refused or await _run(lambda s: {"tables": site_data.owner_summary(s)}, storage)


@router.get("/{table}")
async def rows(project_id: uuid.UUID, table: str, page: int = Query(0, ge=0, le=10_000),
               user_id: uuid.UUID = Depends(get_verified_user_id), session: AsyncSession = Depends(get_session)):
    storage, refused = await _storage_or_refusal(project_id, user_id, session)
    return refused or await _run(site_data.owner_rows, storage, table, page)


@router.patch("/{table}/{row_id}")
async def change(project_id: uuid.UUID, table: str, row_id: str, request: Request,
                 user_id: uuid.UUID = Depends(get_verified_user_id), session: AsyncSession = Depends(get_session)):
    storage, refused = await _storage_or_refusal(project_id, user_id, session)
    return refused or await _run(site_data.owner_update, storage, table, row_id, await request.json())


@router.post("/clear-samples")
async def clear(project_id: uuid.UUID, user_id: uuid.UUID = Depends(get_verified_user_id),
                session: AsyncSession = Depends(get_session)):
    storage, refused = await _storage_or_refusal(project_id, user_id, session)
    return refused or await _run(site_data.clear_samples, storage)


@router.post("/{table}")
async def add(project_id: uuid.UUID, table: str, request: Request,
              user_id: uuid.UUID = Depends(get_verified_user_id), session: AsyncSession = Depends(get_session)):
    storage, refused = await _storage_or_refusal(project_id, user_id, session)
    return refused or await _run(site_data.owner_add, storage, table, await request.json())


@router.delete("/{table}/{row_id}")
async def remove(project_id: uuid.UUID, table: str, row_id: str,
                 user_id: uuid.UUID = Depends(get_verified_user_id), session: AsyncSession = Depends(get_session)):
    storage, refused = await _storage_or_refusal(project_id, user_id, session)
    return refused or await _run(site_data.owner_delete, storage, table, row_id)
