# D:\FYP\FORGE-1\backend\services\projects.py
"""
Projects: the only code that creates, lists or deletes projects (D-174). Every caller - HTTP
routes now, background jobs later - must use `create_project`; nothing else inserts into
`projects`. The database trigger from migration 0001 is the safety net behind this (D-175).

How the 3-project limit stays correct when requests arrive at the same time:
1. One transaction, at READ COMMITTED (set explicitly, so a changed default cannot break it).
2. Lock the owner's row: SELECT ... FROM users WHERE id = :owner FOR UPDATE. A second request
   for the same user waits here until the first one commits or rolls back.
3. Only then count the owner's projects. Under READ COMMITTED each statement sees everything
   committed before it started, so a request that waited sees the project the first one added.
4. Insert only if the count is below the limit, then commit. Any error rolls everything back.
Requests for different users lock different rows, so they never wait for each other.
"""
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.session import sqlstate
from backend.db.tables import Project, User

MAX_PROJECTS_PER_USER = 3
LOCK_TIMEOUT_MS = settings.DB_LOCK_TIMEOUT_MS

# PostgreSQL error codes this service turns into clear answers
_LIMIT_REACHED = "FG001"      # raised by the trigger forge_enforce_project_limit
_LOCK_NOT_AVAILABLE = "55P03"  # lock_timeout expired
_UNIQUE_VIOLATION = "23505"
_FOREIGN_KEY_VIOLATION = "23503"


class ProjectError(Exception):
    """Base class: a project request the user can be told about."""


class UserNotFound(ProjectError):
    pass


class ProjectLimitReached(ProjectError):
    pass


class ProjectNameTaken(ProjectError):
    pass


class ProjectBusy(ProjectError):
    """Another request held this user's lock for longer than LOCK_TIMEOUT_MS."""


async def _insert(session: AsyncSession, project: Project) -> None:
    session.add(project)
    await session.flush()


async def create_project(session: AsyncSession, owner_id: uuid.UUID, name: str,
                         description: str | None = None) -> Project:
    """Create a project if the owner has fewer than MAX_PROJECTS_PER_USER. Commits on success."""
    if session.in_transaction():
        raise RuntimeError("create_project needs a session with no open transaction")
    try:
        async with session.begin():
            await session.connection(execution_options={"isolation_level": "READ COMMITTED"})
            await session.execute(select(func.set_config("lock_timeout", f"{LOCK_TIMEOUT_MS}ms", True)))

            owner = await session.scalar(select(User.id).where(User.id == owner_id).with_for_update())
            if owner is None:
                raise UserNotFound(owner_id)

            existing = await session.scalar(select(func.count()).select_from(Project).where(Project.owner_id == owner_id))
            if existing >= MAX_PROJECTS_PER_USER:
                raise ProjectLimitReached(owner_id)

            project = Project(owner_id=owner_id, name=name, description=description)
            await _insert(session, project)
            await session.refresh(project)
        return project
    except DBAPIError as error:
        code = sqlstate(error)
        if code == _LIMIT_REACHED:
            raise ProjectLimitReached(owner_id) from error
        if code == _LOCK_NOT_AVAILABLE:
            raise ProjectBusy(owner_id) from error
        if code == _UNIQUE_VIOLATION:
            raise ProjectNameTaken(name) from error
        if code == _FOREIGN_KEY_VIOLATION:
            raise UserNotFound(owner_id) from error
        raise


async def list_projects(session: AsyncSession, owner_id: uuid.UUID) -> list[Project]:
    async with session.begin():  # short transaction, closed before returning (rows stay loaded)
        result = await session.scalars(
            select(Project).where(Project.owner_id == owner_id).order_by(Project.created_at, Project.id)
        )
        return list(result)


async def delete_project(session: AsyncSession, owner_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    """Delete for good (D-174). False when the project does not exist or belongs to someone else."""
    async with session.begin():
        deleted = await session.scalar(
            delete(Project).where(Project.id == project_id, Project.owner_id == owner_id).returning(Project.id)
        )
    return deleted is not None
