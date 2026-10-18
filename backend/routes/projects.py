# D:\FYP\FORGE-1\backend\routes\projects.py
"""
Projects API (D-174): list, create (at most 3 per user) and delete for good. All work happens in
backend/services/projects.py; this file only maps its results to HTTP answers. Deleting a project
also deletes its website requests and their paused runs (D-180).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.deps import get_current_user_id, get_verified_user_id
from backend.db.session import get_session
from backend.models.projects import CreateProject, ProjectOut
from backend.services import projects as service
from backend.services import requests as request_service

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def _problem(code: int, kind: str, message: str, headers: dict | None = None) -> HTTPException:
    return HTTPException(code, detail={"code": kind, "message": message}, headers=headers)


@router.get("", response_model=list[ProjectOut])
async def list_projects(user_id: uuid.UUID = Depends(get_current_user_id),
                        session: AsyncSession = Depends(get_session)):
    return await service.list_projects(session, user_id)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProject, user_id: uuid.UUID = Depends(get_verified_user_id),
                         session: AsyncSession = Depends(get_session)):
    try:
        return await service.create_project(session, user_id, body.name, body.description)
    except service.ProjectLimitReached:
        raise _problem(status.HTTP_409_CONFLICT, "project_limit_reached",
                       f"You can have up to {service.MAX_PROJECTS_PER_USER} projects. Delete one to create another.")
    except service.ProjectNameTaken:
        raise _problem(status.HTTP_409_CONFLICT, "project_name_taken", "You already have a project with this name.")
    except service.UserNotFound:
        raise _problem(status.HTTP_404_NOT_FOUND, "user_not_found", "Your account was not found. Please sign in again.")
    except service.ProjectBusy:
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "busy",
                       "Another change to your projects is still running. Please try again.", {"Retry-After": "1"})


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: uuid.UUID, http: Request, user_id: uuid.UUID = Depends(get_current_user_id),
                         session: AsyncSession = Depends(get_session)):
    request_ids = await service.delete_project(session, user_id, project_id)
    if request_ids is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "project_not_found", "Project not found.")
    await request_service.delete_runs(http.app.state.forge_graph.checkpointer, request_ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
