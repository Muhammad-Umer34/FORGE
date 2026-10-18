# D:\FYP\FORGE-1\backend\core\deps.py
"""Shared FastAPI dependencies."""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core import security

_bearer = HTTPBearer(auto_error=False)


async def get_access_claims(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> security.AccessClaims:
    """The access token in "Authorization: Bearer ..." (D-176). Checks the token only (no database
    call); services still handle a user deleted since."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.", headers={"WWW-Authenticate": "Bearer"})
    try:
        return security.decode_access(credentials.credentials)
    except security.InvalidToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your sign-in has expired. Please sign in again.",
                            headers={"WWW-Authenticate": "Bearer"})


async def get_current_user_id(claims: security.AccessClaims = Depends(get_access_claims)) -> uuid.UUID:
    """Any signed-in user, verified or not."""
    return claims.user_id


async def get_verified_user_id(claims: security.AccessClaims = Depends(get_access_claims)) -> uuid.UUID:
    """A signed-in user whose email is verified: needed to create projects and run requests (D-188)."""
    if not claims.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={
            "code": "email_not_verified",
            "message": "Please verify your email address first. Check your inbox for the link we sent.",
        })
    return claims.user_id
