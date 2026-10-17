# D:\FYP\FORGE-1\backend\core\deps.py
"""Shared FastAPI dependencies."""
import uuid

from fastapi import HTTPException, status


async def get_current_user_id() -> uuid.UUID:
    """The signed-in user. Sign-in (JWT access tokens) is the next step of the auth plan; until it
    exists every protected route answers 401, so no project route is reachable without a user.
    Tests replace this dependency."""
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in is not available yet.")
