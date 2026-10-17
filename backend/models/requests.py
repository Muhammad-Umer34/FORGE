# D:\FYP\FORGE-1\backend\models\requests.py
"""Request bodies and the single response envelope of the website-request API (v6 Sections 4 and 18)."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# The answer bodies are the same models the graph validates on resume.
from agents.clarification.schemas import ConfirmationDecision, UserAnswer

RequestStatus = Literal[
    "needs_clarification", "awaiting_confirmation", "complete", "out_of_scope", "failed", "cancelled",
    "reply",   # not a website request: data = {kind, message}; no run to resume (D-150)
]


class CreateRequest(BaseModel):
    """The project comes from the URL (/api/projects/{project_id}/requests), D-179."""
    prompt: str = Field(..., min_length=1, max_length=4000, description="The user's website request, in plain words")


class RequestEnvelope(BaseModel):
    request_id: str
    status: RequestStatus
    data: dict[str, Any] = Field(default_factory=dict)


class RequestSummary(BaseModel):
    """One line in a project's list of requests. 'processing' while the agent is still running."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt: str
    status: Literal["processing"] | RequestStatus
    created_at: datetime
    updated_at: datetime


__all__ = ["CreateRequest", "RequestEnvelope", "RequestStatus", "RequestSummary", "UserAnswer", "ConfirmationDecision"]
