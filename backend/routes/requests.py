# D:\FYP\FORGE-1\backend\routes\requests.py
"""
Website-request API (v6 Section 18, D-130). Starts a FORGE run, returns its pending question or
confirmation screen, and resumes it with the user's answer. One run = one LangGraph thread
(thread id = request id); paused runs live in the checkpointer opened in main.py.

Every request belongs to a project of the signed-in, verified user (D-179, D-188): the routes live under
/api/projects/{project_id}/requests, and each one first checks that the request is in that project
and the project is the user's - otherwise 404, before the agent graph is touched. The API layer
records each request and its latest status in the database; agents never do (D-133).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from agents import logo_colours

from agents.catalogue import load_catalogue
from agents.clarification import slots
from agents.clarification.prompts import PROMPT_VERSIONS
from agents.gateway import model_for, provider
from agents.state import Question, RequestInfo, RunConfig, initial_state
from backend.core.config import settings
from backend.core.deps import get_verified_user_id
from backend.db.session import get_session
from backend.models.requests import ConfirmationDecision, CreateRequest, RequestEnvelope, RequestSummary, UserAnswer
from backend.services import limits
from backend.services import requests as service

router = APIRouter(prefix="/api/projects/{project_id}/requests", tags=["Requests"])


def _config(request_id: str) -> dict:
    return {"configurable": {"thread_id": request_id}}


def _run_config() -> RunConfig:
    cat = load_catalogue()
    return RunConfig(
        model_per_task={"clarification": f"{provider()}/{model_for('clarification')}"},
        catalogue_version=cat.version,
        catalogue_hash=cat.catalogue_hash,
        unsupported_list_hash=cat.unsupported_list_hash,
        baselines_hash=cat.baselines_hash,
        prompt_versions={f"clarification.{k}": v for k, v in PROMPT_VERSIONS.items()},
    )


def _envelope(request_id: str, values: dict, interrupts) -> RequestEnvelope:
    if interrupts:
        payload = interrupts[0].value
        kind = "needs_clarification" if payload.get("type") == "question" else "awaiting_confirmation"
        return RequestEnvelope(request_id=request_id, status=kind, data=payload)

    c = values["clarification"]
    if c.status == "done":
        brief = values["brief"]
        return RequestEnvelope(request_id=request_id, status="complete", data={
            "requirement": brief.model_dump(mode="json", exclude={"test_cases"}),
            "test_cases": [t.model_dump(mode="json") for t in brief.test_cases],
        })
    if c.status == "out_of_scope" and c.out_of_scope:
        return RequestEnvelope(request_id=request_id, status="out_of_scope", data=c.out_of_scope.model_dump())
    if c.status == "replied" and c.reply:
        return RequestEnvelope(request_id=request_id, status="reply", data=c.reply.model_dump())
    if c.status == "cancelled":
        return RequestEnvelope(request_id=request_id, status="cancelled")
    failure = c.failure
    return RequestEnvelope(request_id=request_id, status="failed", data={
        "category": failure.category if failure else "system",
        "message": failure.message if failure else "The request could not be completed.",
        "missing": failure.missing if failure else [],
    })


async def _run(http: Request, request_id: str, graph_input) -> RequestEnvelope:
    graph = http.app.state.forge_graph
    try:
        await graph.ainvoke(graph_input, _config(request_id))
    except Exception as error:   # a bug, not a user problem: never shown as "please rephrase"
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "FORGE had a technical problem. Your request was fine. Please try again.") from error
    snapshot = await graph.aget_state(_config(request_id))
    return _envelope(request_id, snapshot.values, snapshot.interrupts)


async def _owned_request(project_id: uuid.UUID, request_id: str, user_id: uuid.UUID = Depends(get_verified_user_id),
                         session: AsyncSession = Depends(get_session)) -> str:
    """The request id, once it is known to be in this project of the signed-in user."""
    try:
        await service.require_request(session, user_id, project_id, request_id)
    except service.RequestNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown request id")
    return request_id


async def _record(http: Request, session: AsyncSession, envelope: RequestEnvelope) -> RequestEnvelope:
    """Save the outcome. A greeting or question about FORGE (status 'reply') is not kept at all."""
    checkpointer = http.app.state.forge_graph.checkpointer
    if envelope.status == "reply":
        await service.forget_request(session, envelope.request_id)
        await service.delete_runs(checkpointer, [envelope.request_id])
    elif not await service.record_status(session, envelope.request_id, envelope.status):
        await service.delete_runs(checkpointer, [envelope.request_id])  # project deleted during the run
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This project was deleted.")
    return envelope


def _limited(error: limits.RateLimited, message: str) -> HTTPException:
    minutes = max(1, round(error.retry_after_s / 60))
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"{message} Please try again in about {minutes} minute(s).",
                         headers={"Retry-After": str(error.retry_after_s)})


_STILL_WORKING = "FORGE is still working on your last step. Please wait for it to finish."


async def _pending(http: Request, request_id: str, expected: str) -> dict:
    snapshot = await http.app.state.forge_graph.aget_state(_config(request_id))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown request id")
    payload = snapshot.interrupts[0].value if snapshot.interrupts else None
    if not payload or payload.get("type") != expected:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This request is not waiting for a {expected}")
    return payload


@router.get("", response_model=list[RequestSummary])
async def list_requests(project_id: uuid.UUID, user_id: uuid.UUID = Depends(get_verified_user_id),
                        session: AsyncSession = Depends(get_session)):
    try:
        return await service.list_requests(session, user_id, project_id)
    except service.ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")


@router.post("", response_model=RequestEnvelope)
async def create_request(project_id: uuid.UUID, body: CreateRequest, http: Request,
                         user_id: uuid.UUID = Depends(get_verified_user_id), session: AsyncSession = Depends(get_session)):
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    rules = ((f"requests:user:{user_id}", settings.LIMIT_REQUESTS_PER_USER_DAY, limits.DAY),
             ("requests:all", settings.LIMIT_REQUESTS_PER_DAY, limits.DAY))
    try:  # every request runs the model, so it is limited per user and for the whole app (D-191)
        await limits.take(session, *rules)
    except limits.RateLimited as error:
        raise _limited(error, "You have reached today's limit of website requests.")
    try:
        await service.start_request(session, user_id, project_id, request_id, body.prompt)
    except service.ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    state = initial_state(
        RequestInfo(request_id=request_id, user_id=str(user_id), project_id=str(project_id),
                    prompt=body.prompt, created_at=datetime.now(timezone.utc)),
        config=_run_config(),
    )
    try:
        envelope = await _run(http, request_id, state)
    except HTTPException:  # our failure (e.g. the model is down): not left at "processing", not counted
        await service.record_status(session, request_id, "failed")
        await limits.give_back(session, *rules)
        raise
    return await _record(http, session, envelope)


@router.get("/{request_id}", response_model=RequestEnvelope)
async def get_request(http: Request, request_id: str = Depends(_owned_request)):
    snapshot = await http.app.state.forge_graph.aget_state(_config(request_id))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown request id")
    return _envelope(request_id, snapshot.values, snapshot.interrupts)


@router.post("/{request_id}/answer", response_model=RequestEnvelope)
async def answer_question(body: UserAnswer, http: Request, request_id: str = Depends(_owned_request),
                          session: AsyncSession = Depends(get_session)):
    try:
        async with service.one_step_at_a_time(request_id):
            payload = await _pending(http, request_id, "question")
            question = Question.model_validate({k: v for k, v in payload.items() if k != "type"})
            error = slots.validate_answer(question, body)
            if error:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, error)
            return await _record(http, session, await _run(http, request_id, Command(resume=body.model_dump())))
    except service.RunInProgress:
        raise HTTPException(status.HTTP_409_CONFLICT, _STILL_WORKING)


@router.post("/{request_id}/confirmation", response_model=RequestEnvelope)
async def confirm_brief(body: ConfirmationDecision, http: Request, request_id: str = Depends(_owned_request),
                        user_id: uuid.UUID = Depends(get_verified_user_id), session: AsyncSession = Depends(get_session)):
    try:
        async with service.one_step_at_a_time(request_id):
            return await _confirm(body, http, request_id, user_id, session)
    except service.RunInProgress:
        raise HTTPException(status.HTTP_409_CONFLICT, _STILL_WORKING)


async def _confirm(body: ConfirmationDecision, http: Request, request_id: str, user_id: uuid.UUID,
                   session: AsyncSession) -> RequestEnvelope:
    payload = await _pending(http, request_id, "confirmation")
    if body.decision not in payload["actions"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"'{body.decision}' is not available now")
    if body.decision == "edit" and not (body.edit_text or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "edit_text is required for an edit")
    if body.decision == "theme_source":
        source = body.theme_source
        if source is None or not payload["theme_sources_left"].get(source.kind):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "This theme source can't be used again for this request")
        if source.kind == "website" and not (source.url or "").strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please paste a website address")
        if source.kind == "logo" and not source.colour:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please choose one of the logo colours")
        if source.kind == "website":  # each read starts a browser (D-193)
            try:
                await limits.take(session, (f"website-reads:user:{user_id}", settings.LIMIT_WEBSITE_READS_PER_USER_DAY, limits.DAY))
            except limits.RateLimited as error:
                raise _limited(error, "You have reached today's limit for reading websites.")
    return await _record(http, session, await _run(http, request_id, Command(resume=body.model_dump())))


@router.post("/{request_id}/image")
async def read_image_colours(http: Request, request_id: str = Depends(_owned_request), file: UploadFile = File(...),
                             kind: str = Query("logo", pattern="^(logo|screenshot)$"),
                             user_id: uuid.UUID = Depends(get_verified_user_id), session: AsyncSession = Depends(get_session)):
    """
    Colours from an uploaded logo or website screenshot (theme Phase 2, D-163, D-164). Local code only
    (Pillow + Material quantizer), no model call. The image is read in memory and never stored; the user
    then picks a colour and sends it as a 'theme_source' confirmation decision.
    """
    await _pending(http, request_id, "confirmation")
    try:
        await limits.take(session, (f"image-reads:user:{user_id}", settings.LIMIT_IMAGE_READS_PER_USER_HOUR, limits.HOUR))
    except limits.RateLimited as error:
        raise _limited(error, "You have uploaded many images in the last hour.")
    data = await file.read(logo_colours.MAX_BYTES + 1)
    try:
        extract = logo_colours.logo_colours if kind == "logo" else logo_colours.screenshot_colours
        return await run_in_threadpool(extract, data)
    except logo_colours.ImageError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
