# D:\FYP\FORGE-1\backend\services\requests.py
"""
Which website requests belong to which project and user (D-179, D-180). Agents never touch the
database (D-133); the request routes call this before and after running the agent graph.

Every look-up joins requests -> projects and filters by the signed-in owner, so a request id
from someone else's project is simply "not found" - nobody can learn that it exists.
Paused runs live in the LangGraph checkpointer (thread id = request id); `delete_runs` removes
them when their project is deleted.
"""
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import sqlstate
from backend.db.tables import Project, WebsiteRequest

logger = logging.getLogger(__name__)
_FOREIGN_KEY_VIOLATION = "23503"


class ProjectNotFound(Exception):
    pass


class RequestNotFound(Exception):
    pass


class WebsiteInProgress(Exception):
    """The project already has a website being described, paused, or with a finished brief."""


# One project = one website: a new request may start only when the latest one ended without a website
# (failed, out of scope or cancelled). "Start over" cancels the current one first.
ACTIVE_STATUSES = ("processing", "needs_clarification", "awaiting_confirmation", "complete", "paused")


async def start_request(session: AsyncSession, owner_id: uuid.UUID, project_id: uuid.UUID,
                        request_id: str, prompt: str) -> None:
    """Record a new request in the owner's project, before the agent runs. The project row is locked, so two
    requests sent at once cannot both start a website."""
    try:
        async with session.begin():
            owned = await session.scalar(select(Project.id).where(Project.id == project_id, Project.owner_id == owner_id)
                                         .with_for_update())
            if owned is None:
                raise ProjectNotFound(project_id)
            latest = await session.scalar(select(WebsiteRequest.status).where(WebsiteRequest.project_id == project_id)
                                          .order_by(WebsiteRequest.created_at.desc()).limit(1))
            if latest in ACTIVE_STATUSES:
                raise WebsiteInProgress(project_id)
            session.add(WebsiteRequest(id=request_id, project_id=project_id, prompt=prompt))
    except DBAPIError as error:
        if sqlstate(error) == _FOREIGN_KEY_VIOLATION:  # the project was deleted a moment ago
            raise ProjectNotFound(project_id) from error
        raise


async def require_request(session: AsyncSession, owner_id: uuid.UUID, project_id: uuid.UUID, request_id: str) -> None:
    """Raise RequestNotFound unless the request is in this project and the project is the owner's."""
    async with session.begin():
        found = await session.scalar(
            select(WebsiteRequest.id).join(Project, Project.id == WebsiteRequest.project_id)
            .where(WebsiteRequest.id == request_id, WebsiteRequest.project_id == project_id, Project.owner_id == owner_id)
        )
    if found is None:
        raise RequestNotFound(request_id)


async def list_requests(session: AsyncSession, owner_id: uuid.UUID, project_id: uuid.UUID) -> list[WebsiteRequest]:
    async with session.begin():
        owned = await session.scalar(select(Project.id).where(Project.id == project_id, Project.owner_id == owner_id))
        if owned is None:
            raise ProjectNotFound(project_id)
        result = await session.scalars(select(WebsiteRequest).where(WebsiteRequest.project_id == project_id)
                                       .order_by(WebsiteRequest.created_at.desc(), WebsiteRequest.id))
        return list(result)


async def record_status(session: AsyncSession, request_id: str, status: str) -> bool:
    """Save the latest envelope status. False if the request is gone (its project was deleted)."""
    async with session.begin():
        updated = await session.scalar(
            update(WebsiteRequest).where(WebsiteRequest.id == request_id)
            .values(status=status, updated_at=datetime.now(timezone.utc)).returning(WebsiteRequest.id)
        )
    return updated is not None


async def sync_status(session: AsyncSession, request_id: str, status: str) -> None:
    """Correct a stored status that no longer matches the run (only writes when it differs)."""
    async with session.begin():
        await session.execute(update(WebsiteRequest)
                              .where(WebsiteRequest.id == request_id, WebsiteRequest.status != status)
                              .values(status=status, updated_at=datetime.now(timezone.utc)))


async def stored_status(session: AsyncSession, request_id: str) -> str | None:
    async with session.begin():
        return await session.scalar(select(WebsiteRequest.status).where(WebsiteRequest.id == request_id))


async def processing_request_ids(session: AsyncSession) -> list[str]:
    """Requests still marked as running: after a crash nobody could update them."""
    async with session.begin():
        return list(await session.scalars(select(WebsiteRequest.id).where(WebsiteRequest.status == "processing")))


async def forget_request(session: AsyncSession, request_id: str) -> None:
    """Remove a request that turned out not to be a website request (a greeting or a question, D-150)."""
    async with session.begin():
        await session.execute(delete(WebsiteRequest).where(WebsiteRequest.id == request_id))


async def delete_runs(checkpointer, request_ids: list[str]) -> None:
    """Delete paused runs from the checkpointer. A failure is logged, not raised: the database rows
    are already gone, so a leftover run can no longer be reached by anyone."""
    for request_id in request_ids:
        try:
            await checkpointer.adelete_thread(request_id)
        except Exception:
            logger.exception("Could not delete the paused run %s", request_id)


class RunInProgress(Exception):
    """This request is already running an agent step (D-190)."""


_running: set[str] = set()


@asynccontextmanager
async def one_step_at_a_time(request_id: str):
    """Refuse a second answer or confirmation while the first is still running, so a double click or
    a second tab cannot run the model twice and lose one of the answers. The server runs as one
    process (the checkpointer is a SQLite file), so a set in memory is enough; checking and adding
    happen with no await in between, so two calls cannot both get in."""
    if request_id in _running:
        raise RunInProgress(request_id)
    _running.add(request_id)
    try:
        yield
    finally:
        _running.discard(request_id)


# Where a run stands, read from its saved checkpoint (persistence plan):
#   missing           nothing saved (never started, or the checkpoint was lost)
#   waiting_for_user  paused at a question or the confirmation screen
#   finished          reached its end (complete, out of scope, cancelled, or failed for a user reason)
#   working           steps left and a step is running right now in this server
#   paused            steps left, nothing running: it stopped (crash, model outage) and can be continued
async def run_state(graph, request_id: str, count_running: bool = True):
    """(state, snapshot). Pass count_running=False when the caller already holds `one_step_at_a_time`.
    shortcut: "running right now" is this process's memory; with several server processes it must move to the database."""
    snapshot = await graph.aget_state({"configurable": {"thread_id": request_id}})
    if not snapshot.values:
        return "missing", snapshot
    if snapshot.interrupts:
        return "waiting_for_user", snapshot
    if not snapshot.next:
        return "finished", snapshot
    if count_running and request_id in _running:
        return "working", snapshot
    return "paused", snapshot
