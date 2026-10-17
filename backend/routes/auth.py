# D:\FYP\FORGE-1\backend\routes\auth.py
"""
Sign-in API (D-176 - D-178): register, login, refresh, logout, me. All rules live in
backend/services/auth.py; this file maps results to HTTP and sets or clears the refresh cookie.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.deps import get_current_user_id
from backend.db.session import get_session
from backend.models.auth import LoginBody, RegisterBody, TokenOut, UserOut
from backend.services import auth as service

router = APIRouter(prefix="/api/auth", tags=["Auth"])

REFRESH_COOKIE = "forge_refresh"
REFRESH_COOKIE_PATH = "/api/auth"  # the browser sends it only to these endpoints


def _problem(code: int, kind: str, message: str, headers: dict | None = None) -> HTTPException:
    return HTTPException(code, detail={"code": kind, "message": message}, headers=headers)


def _signed_in(response: Response, result: service.SignIn) -> TokenOut:
    now = datetime.now(timezone.utc)
    response.set_cookie(REFRESH_COOKIE, result.refresh_token, max_age=int((result.refresh_expires_at - now).total_seconds()),
                        path=REFRESH_COOKIE_PATH, httponly=True, secure=settings.COOKIE_SECURE, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return TokenOut(access_token=result.access_token, expires_in=int((result.access_expires_at - now).total_seconds()),
                    user=UserOut.model_validate(result.user))


def _signed_out(code: int, kind: str, message: str) -> JSONResponse:
    """An error answer that also removes the refresh cookie."""
    response = JSONResponse({"detail": {"code": kind, "message": message}}, status_code=code)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True,
                           secure=settings.COOKIE_SECURE, samesite="lax")
    return response


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterBody, request: Request, response: Response,
                   session: AsyncSession = Depends(get_session)):
    try:
        result = await service.register(session, body.email, body.password, body.display_name,
                                        request.headers.get("user-agent"))
    except service.EmailTaken:
        raise _problem(status.HTTP_409_CONFLICT, "email_taken", "An account with this email already exists. Please sign in.")
    return _signed_in(response, result)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginBody, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    try:
        result = await service.login(session, body.email, body.password, request.headers.get("user-agent"))
    except service.InvalidCredentials:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "The email or password is not correct.")
    except service.AccountLocked as locked:
        minutes = max(1, round(locked.retry_after_s / 60))
        raise _problem(status.HTTP_429_TOO_MANY_REQUESTS, "account_locked",
                       f"Too many wrong passwords. Please try again in about {minutes} minute(s).",
                       {"Retry-After": str(locked.retry_after_s)})
    return _signed_in(response, result)


@router.post("/refresh", response_model=TokenOut)
async def refresh(request: Request, response: Response, session: AsyncSession = Depends(get_session),
                  forge_refresh: str | None = Cookie(default=None)):
    try:
        result = await service.refresh(session, forge_refresh, request.headers.get("user-agent"))
    except service.RefreshRaced:
        # Another tab refreshed a moment ago and the browser already has its new cookie: keep it.
        raise _problem(status.HTTP_409_CONFLICT, "refresh_in_progress", "Please try again.")
    except service.InvalidRefresh:
        return _signed_out(status.HTTP_401_UNAUTHORIZED, "signed_out", "Please sign in again.")
    return _signed_in(response, result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session: AsyncSession = Depends(get_session), forge_refresh: str | None = Cookie(default=None)):
    await service.logout(session, forge_refresh)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True,
                           secure=settings.COOKIE_SECURE, samesite="lax")
    return response


@router.get("/me", response_model=UserOut)
async def me(user_id: uuid.UUID = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)):
    user = await service.get_user(session, user_id)
    if user is None:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "signed_out", "Please sign in again.")
    return user
