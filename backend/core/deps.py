# D:\FYP\FORGE-1\backend\core\deps.py
"""Shared FastAPI dependencies."""
import ipaddress
import uuid

from fastapi import Depends, HTTPException, Request, status
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


def client_ip(request: Request) -> str:
    """The visitor's address, for rate limits (D-189). The browser talks to Next.js, which forwards
    to us and adds X-Forwarded-For. That header is trusted only when the request comes from this
    machine (our own Next.js server); from anywhere else it could be faked, so the direct address is used."""
    direct = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for", "")
    try:
        if forwarded and ipaddress.ip_address(direct).is_loopback:
            first = ipaddress.ip_address(forwarded.split(",")[0].strip())  # ignore anything that is not an address
            return str(getattr(first, "ipv4_mapped", None) or first)    # Node reports IPv4 as ::ffff:1.2.3.4
    except ValueError:
        pass
    return direct
