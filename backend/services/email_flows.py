# D:\FYP\FORGE-1\backend\services\email_flows.py
"""
Email verification and password reset (D-185, D-186). The only code that creates or uses the
one-time links sent by email.

- A link carries a random token (256 bits). Only its SHA-256 hash is stored, so a database leak
  gives no usable links. Each link works once and expires (verify: 24 h, reset: 30 min).
- Asking for a new link cancels the older unused ones of the same kind, and at most
  MAX_EMAILS_PER_HOUR links of one kind are made per account per hour.
- "Forgot password" never says whether an email has an account (the route always gives the same
  answer). A successful reset also unlocks the account, verifies the email (the link proved the
  user reads it) and signs the account out everywhere.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core import security
from backend.core.config import settings
from backend.db.tables import AuthToken, RefreshToken, User

VERIFY_EMAIL = "verify_email"
RESET_PASSWORD = "reset_password"
LIFETIME = {VERIFY_EMAIL: timedelta(hours=24), RESET_PASSWORD: timedelta(minutes=30)}
MAX_EMAILS_PER_HOUR = 3


class EmailFlowError(Exception):
    """Base class: a problem with an email link the user can be told about."""


class InvalidLink(EmailFlowError):
    """Unknown, used, expired or cancelled link."""


class AlreadyVerified(EmailFlowError):
    pass


class TooManyEmails(EmailFlowError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def new_link_token(session: AsyncSession, user_id: uuid.UUID, purpose: str, now: datetime | None = None) -> str:
    """Make a one-time token inside the caller's transaction; older unused ones stop working."""
    now = now or _now()
    await session.execute(
        update(AuthToken).where(AuthToken.user_id == user_id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(32)
    session.add(AuthToken(user_id=user_id, purpose=purpose, token_hash=_hash(token), expires_at=now + LIFETIME[purpose]))
    await session.flush()
    return token


async def _links_in_last_hour(session: AsyncSession, user_id: uuid.UUID, purpose: str, now: datetime) -> int:
    return await session.scalar(
        select(func.count()).select_from(AuthToken)
        .where(AuthToken.user_id == user_id, AuthToken.purpose == purpose, AuthToken.created_at > now - timedelta(hours=1))
    )


async def _use(session: AsyncSession, token: str, purpose: str, now: datetime) -> AuthToken:
    """Lock and spend a token; two clicks at once cannot both succeed."""
    row = await session.scalar(
        select(AuthToken).where(AuthToken.token_hash == _hash(token), AuthToken.purpose == purpose).with_for_update()
    )
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise InvalidLink()
    row.used_at = now
    return row


async def resend_verification(session: AsyncSession, user_id: uuid.UUID) -> tuple[User, str]:
    """A fresh verification link for a signed-in user."""
    async with session.begin():
        now = _now()
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None or not user.is_active:
            raise InvalidLink()
        if user.email_verified_at is not None:
            raise AlreadyVerified()
        if await _links_in_last_hour(session, user_id, VERIFY_EMAIL, now) >= MAX_EMAILS_PER_HOUR:
            raise TooManyEmails()
        token = await new_link_token(session, user_id, VERIFY_EMAIL, now)
    return user, token


async def verify_email(session: AsyncSession, token: str) -> User:
    async with session.begin():
        now = _now()
        outcome: EmailFlowError | None = None
        try:
            row = await _use(session, token, VERIFY_EMAIL, now)
        except InvalidLink as error:
            outcome = error
        else:
            user = await session.get(User, row.user_id, with_for_update=True)
            if user.email_verified_at is None:
                user.email_verified_at = now
    if outcome:
        raise outcome
    return user


async def start_password_reset(session: AsyncSession, email: str) -> tuple[User, str] | None:
    """A reset link, or None when there is no active account or too many links were sent.
    The route answers the same either way."""
    async with session.begin():
        now = _now()
        user = await session.scalar(
            select(User).where(func.lower(User.email) == email.strip().lower(), User.is_active.is_(True)).with_for_update()
        )
        if user is None or await _links_in_last_hour(session, user.id, RESET_PASSWORD, now) >= MAX_EMAILS_PER_HOUR:
            return None
        token = await new_link_token(session, user.id, RESET_PASSWORD, now)
    return user, token


async def reset_password(session: AsyncSession, token: str, new_password: str) -> User:
    password_hash = await run_in_threadpool(security.hash_password, new_password)
    outcome: EmailFlowError | None = None
    async with session.begin():
        now = _now()
        try:
            row = await _use(session, token, RESET_PASSWORD, now)
        except InvalidLink as error:
            outcome = error
        else:
            user = await session.get(User, row.user_id, with_for_update=True)
            user.password_hash = password_hash
            user.failed_logins, user.locked_until = 0, None
            if user.email_verified_at is None:
                user.email_verified_at = now
            user.updated_at = now
            await session.execute(  # signed out on every device
                update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)).values(revoked_at=now)
            )
    if outcome:
        raise outcome
    return user


def link(path: str, token: str) -> str:
    """The frontend page that receives the token, e.g. /verify-email?token=..."""
    return f"{settings.FRONTEND_URL}{path}?token={token}"
