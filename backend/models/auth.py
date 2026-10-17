# D:\FYP\FORGE-1\backend\models\auth.py
"""Request and response bodies for sign-in (D-176)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterBody(BaseModel):
    email: EmailStr
    # NIST SP 800-63B: at least 8 characters, long passphrases allowed, no composition rules
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value

    @field_validator("password")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot be only spaces.")
        return value


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    created_at: datetime


class TokenOut(BaseModel):
    """The access token goes in the body (the frontend keeps it in memory); the refresh token only
    in the HttpOnly cookie, so page scripts can never read it."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
