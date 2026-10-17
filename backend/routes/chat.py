# D:\FYP\FORGE-1\backend\routes\chat.py
from fastapi import APIRouter, HTTPException, status

from backend.models.chat import ChatRequest, ChatResponse, ResetRequest, ResetResponse
from backend.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def handle_chat_message(payload: ChatRequest):
    user_text = payload.message.strip()
    if not user_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    response = chat_service.process_message(
        user_message=user_text,
        session_id=payload.session_id
    )
    return response


@router.post("/reset", response_model=ResetResponse)
def handle_reset_session(payload: ResetRequest):
    success = chat_service.reset_session(payload.session_id)
    return ResetResponse(
        status="reset",
        session_id=payload.session_id,
        success=success
    )
