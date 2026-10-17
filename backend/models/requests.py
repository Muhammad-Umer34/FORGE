# D:\FYP\FORGE-1\backend\models\requests.py
"""Request bodies and the single response envelope of the website-request API (v6 Sections 4 and 18)."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# The answer bodies are the same models the graph validates on resume.
from agents.clarification.schemas import ConfirmationDecision, UserAnswer

RequestStatus = Literal[
    "needs_clarification", "awaiting_confirmation", "complete", "out_of_scope", "failed", "cancelled",
]


class CreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="The user's website request, in plain words")
    project_id: Optional[str] = Field(None, description="Project this request belongs to")


class RequestEnvelope(BaseModel):
    request_id: str
    status: RequestStatus
    data: dict[str, Any] = Field(default_factory=dict)


__all__ = ["CreateRequest", "RequestEnvelope", "RequestStatus", "UserAnswer", "ConfirmationDecision"]
