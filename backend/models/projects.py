# D:\FYP\FORGE-1\backend\models\projects.py
"""Request and response bodies for the projects API (D-174)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateProject(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be empty.")
        return value


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
