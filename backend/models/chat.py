# D:\FYP\FORGE-1\backend\models\chat.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ChatIntent(str, Enum):
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"
    WEBSITE_BUILD = "website_build"
    GENERAL = "general"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or requirement message for FORGE")
    session_id: Optional[str] = Field(None, description="Unique conversation session ID for memory tracking")


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Active session ID")
    reply: str = Field(..., description="FORGE agent reply")
    intent: ChatIntent = Field(..., description="Detected conversation intent")
    turn_count: int = Field(..., description="Number of completed conversation turns in this session")


class ResetRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to clear from memory")


class ResetResponse(BaseModel):
    status: str = Field(default="reset")
    session_id: str
    success: bool
