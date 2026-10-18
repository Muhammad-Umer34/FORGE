# D:\FYP\FORGE-1\backend\routes\auth.py
"""
Sign-in API (D-176 - D-178): register, login, refresh, logout, me; email verification and password
reset (D-185, D-186). All rules live in backend/services/auth.py and email_flows.py; this file maps
results to HTTP, sets or clears the refresh cookie, and queues emails to send after the answer.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.deps import get_current_user_id
from backend.db.session import get_session
from backend.models.auth import (EmailBody, LoginBody, MessageOut, RegisterBody, ResetPasswordBody, TokenBody,
                                 TokenOut, UserOut)
from backend.services import auth as service
from backend.services import email_flows, mailer

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
async def register(body: RegisterBody, request: Request, response: Response, background: BackgroundTasks,
                   session: AsyncSession = Depends(get_session)):
    try:
        result = await service.register(session, body.email, body.password, body.display_name,
                                        request.headers.get("user-agent"))
    except service.EmailTaken:
        raise _problem(status.HTTP_409_CONFLICT, "email_taken", "An account with this email already exists. Please sign in.")
    background.add_task(mailer.send, mailer.verification_email(
        result.user.email, result.user.display_name, email_flows.link("/verify-email", result.verify_token)))
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


# ---------------------------------------------------------------- email verification and password reset

_INVALID_LINK = "This link is invalid or has expired. Please ask for a new one."
_RESET_SENT = "If an account exists for this email, we have sent a link to reset the password. It expires in 30 minutes."


@router.post("/verify-email", response_model=UserOut)
async def verify_email(body: TokenBody, session: AsyncSession = Depends(get_session)):
    """Opened from the email link. The frontend then refreshes the session to get a verified access token."""
    try:
        return await email_flows.verify_email(session, body.token)
    except email_flows.InvalidLink:
        raise _problem(status.HTTP_400_BAD_REQUEST, "invalid_link", _INVALID_LINK)


@router.post("/resend-verification", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(background: BackgroundTasks, user_id: uuid.UUID = Depends(get_current_user_id),
                              session: AsyncSession = Depends(get_session)):
    try:
        user, token = await email_flows.resend_verification(session, user_id)
    except email_flows.AlreadyVerified:
        raise _problem(status.HTTP_409_CONFLICT, "already_verified", "Your email is already verified.")
    except email_flows.TooManyEmails:
        raise _problem(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_emails",
                       "We have sent several emails already. Please check your inbox and spam folder, or try again in an hour.")
    except email_flows.InvalidLink:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "signed_out", "Please sign in again.")
    background.add_task(mailer.send, mailer.verification_email(user.email, user.display_name, email_flows.link("/verify-email", token)))
    return MessageOut(message=f"We sent a new link to {user.email}.")


@router.post("/forgot-password", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(body: EmailBody, background: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    """The same answer whether or not the email has an account, so nobody can probe for accounts."""
    started = await email_flows.start_password_reset(session, body.email)
    if started:
        user, token = started
        background.add_task(mailer.send, mailer.reset_email(user.email, user.display_name, email_flows.link("/reset-password", token)))
    return MessageOut(message=_RESET_SENT)


@router.post("/reset-password", response_model=MessageOut)
async def reset_password(body: ResetPasswordBody, session: AsyncSession = Depends(get_session)):
    try:
        await email_flows.reset_password(session, body.token, body.password)
    except email_flows.InvalidLink:
        raise _problem(status.HTTP_400_BAD_REQUEST, "invalid_link", _INVALID_LINK)
    return MessageOut(message="Your password has been changed. Please sign in with your new password.")
