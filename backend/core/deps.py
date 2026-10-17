# D:\FYP\FORGE-1\backend\core\deps.py
"""Shared FastAPI dependencies."""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core import security

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> uuid.UUID:
    """The signed-in user, from the access token in "Authorization: Bearer ..." (D-176).
    Checks the token only (no database call); services still handle a user deleted since."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.", headers={"WWW-Authenticate": "Bearer"})
    try:
        return security.decode_access_token(credentials.credentials)
    except security.InvalidToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your sign-in has expired. Please sign in again.",
                            headers={"WWW-Authenticate": "Bearer"})
