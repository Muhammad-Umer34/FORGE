# D:\FYP\FORGE-1\backend\routes\requests.py
"""
Website-request API (v6 Section 18, D-130). Starts a FORGE run, returns its pending question or
confirmation screen, and resumes it with the user's answer. One run = one LangGraph thread
(thread id = request id). Nothing is saved to the database yet (D-133); paused runs live in the
checkpointer opened in main.py.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from langgraph.types import Command

from agents import logo_colours

from agents.catalogue import load_catalogue
from agents.clarification import slots
from agents.clarification.prompts import PROMPT_VERSIONS
from agents.gateway import model_for
from agents.state import Question, RequestInfo, RunConfig, initial_state
from backend.models.requests import ConfirmationDecision, CreateRequest, RequestEnvelope, UserAnswer

router = APIRouter(prefix="/api/requests", tags=["Requests"])


def _config(request_id: str) -> dict:
    return {"configurable": {"thread_id": request_id}}


def _run_config() -> RunConfig:
    cat = load_catalogue()
    return RunConfig(
        model_per_task={"clarification": f"google/{model_for('clarification')}"},
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


async def _pending(http: Request, request_id: str, expected: str) -> dict:
    snapshot = await http.app.state.forge_graph.aget_state(_config(request_id))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown request id")
    payload = snapshot.interrupts[0].value if snapshot.interrupts else None
    if not payload or payload.get("type") != expected:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This request is not waiting for a {expected}")
    return payload


@router.post("", response_model=RequestEnvelope)
async def create_request(body: CreateRequest, http: Request):
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    state = initial_state(
        RequestInfo(request_id=request_id, user_id="anonymous", project_id=body.project_id or "default",
                    prompt=body.prompt, created_at=datetime.now(timezone.utc)),
        config=_run_config(),
    )
    return await _run(http, request_id, state)


@router.get("/{request_id}", response_model=RequestEnvelope)
async def get_request(request_id: str, http: Request):
    snapshot = await http.app.state.forge_graph.aget_state(_config(request_id))
    if not snapshot.values:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown request id")
    return _envelope(request_id, snapshot.values, snapshot.interrupts)


@router.post("/{request_id}/answer", response_model=RequestEnvelope)
async def answer_question(request_id: str, body: UserAnswer, http: Request):
    payload = await _pending(http, request_id, "question")
    question = Question.model_validate({k: v for k, v in payload.items() if k != "type"})
    error = slots.validate_answer(question, body)
    if error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, error)
    return await _run(http, request_id, Command(resume=body.model_dump()))


@router.post("/{request_id}/confirmation", response_model=RequestEnvelope)
async def confirm_brief(request_id: str, body: ConfirmationDecision, http: Request):
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
    return await _run(http, request_id, Command(resume=body.model_dump()))


@router.post("/{request_id}/image")
async def read_image_colours(request_id: str, http: Request, file: UploadFile = File(...),
                             kind: str = Query("logo", pattern="^(logo|screenshot)$")):
    """
    Colours from an uploaded logo or website screenshot (theme Phase 2, D-163, D-164). Local code only
    (Pillow + Material quantizer), no model call. The image is read in memory and never stored; the user
    then picks a colour and sends it as a 'theme_source' confirmation decision.
    """
    await _pending(http, request_id, "confirmation")
    data = await file.read(logo_colours.MAX_BYTES + 1)
    try:
        extract = logo_colours.logo_colours if kind == "logo" else logo_colours.screenshot_colours
        return await run_in_threadpool(extract, data)
    except logo_colours.ImageError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
