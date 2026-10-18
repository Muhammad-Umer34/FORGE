# D:\FYP\FORGE-1\backend\services\auth.py
"""
Accounts and sign-in sessions (D-176 - D-178). The only code that creates users or issues,
rotates and revokes refresh tokens. Routes map its exceptions to HTTP answers.

- Register and login give an access token (short) and a refresh token (long).
- Wrong password: the user's row is locked while the attempt is counted, so parallel guesses are
  counted exactly. After MAX_FAILED_LOGINS the account is locked for LOCKOUT.
- Unknown email and wrong password give the same answer, and take about the same time.
- Refresh rotates: the presented token is revoked and replaced by a new one in the same family.
  Presenting an already-replaced token later means it was copied (stolen or leaked), so the whole
  family - that sign-in on every device it reached - is revoked. A token replaced only seconds ago
  is just refused, because two tabs refreshing at once is normal, not theft.
"""
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core import security
from backend.db.session import sqlstate
from backend.db.tables import RefreshToken, User
from backend.services import email_flows

MAX_FAILED_LOGINS = 5
LOCKOUT = timedelta(minutes=15)
ROTATION_GRACE = timedelta(seconds=10)
_UNIQUE_VIOLATION = "23505"


class AuthError(Exception):
    """Base class: a sign-in problem the user can be told about."""


class EmailTaken(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class AccountLocked(AuthError):
    def __init__(self, retry_after_s: int):
        super().__init__(retry_after_s)
        self.retry_after_s = retry_after_s


class InvalidRefresh(AuthError):
    pass


class RefreshRaced(InvalidRefresh):
    """The token was replaced seconds ago by another tab. Not theft: the browser already holds the
    new token, so the caller should simply retry."""


@dataclass(frozen=True)
class SignIn:
    user: User
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    verify_token: str | None = None  # set by register: the link to email (D-185)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _begin_read_committed(session: AsyncSession) -> None:
    await session.connection(execution_options={"isolation_level": "READ COMMITTED"})


async def _issue(session: AsyncSession, user: User, family_id: uuid.UUID, user_agent: str | None,
                 now: datetime) -> tuple[SignIn, RefreshToken]:
    refresh, jti, refresh_expires = security.create_refresh_token(user.id, family_id, now)
    row = RefreshToken(id=uuid.uuid4(), user_id=user.id, family_id=family_id, token_hash=security.hash_token_id(jti),
                       expires_at=refresh_expires, user_agent=(user_agent or "")[:255] or None)
    session.add(row)
    await session.flush()
    access, access_expires = security.create_access_token(user.id, now, email_verified=user.email_verified)
    return SignIn(user, access, access_expires, refresh, refresh_expires), row


async def _revoke_family(session: AsyncSession, family_id: uuid.UUID, now: datetime) -> None:
    await session.execute(
        update(RefreshToken).where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


async def register(session: AsyncSession, email: str, password: str, display_name: str,
                   user_agent: str | None = None) -> SignIn:
    password_hash = await run_in_threadpool(security.hash_password, password)
    try:
        async with session.begin():
            user = User(email=email.strip().lower(), password_hash=password_hash, display_name=display_name.strip())
            session.add(user)
            await session.flush()
            await session.refresh(user)
            signed_in, _ = await _issue(session, user, uuid.uuid4(), user_agent, _now())
            token = await email_flows.new_link_token(session, user.id, email_flows.VERIFY_EMAIL)
        return replace(signed_in, verify_token=token)
    except DBAPIError as error:
        if sqlstate(error) == _UNIQUE_VIOLATION:
            raise EmailTaken(email) from error
        raise


async def login(session: AsyncSession, email: str, password: str, user_agent: str | None = None) -> SignIn:
    outcome: AuthError | None = None
    signed_in: SignIn | None = None
    async with session.begin():
        await _begin_read_committed(session)
        now = _now()
        user = await session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()).with_for_update())
        if user is None:
            await run_in_threadpool(security.verify_password, password, None)  # same time as a real check
            outcome = InvalidCredentials()
        elif user.locked_until is not None and user.locked_until > now:
            outcome = AccountLocked(max(1, int((user.locked_until - now).total_seconds())))
        else:
            matches, new_hash = await run_in_threadpool(security.verify_password, password, user.password_hash)
            if not matches:
                user.failed_logins += 1
                if user.failed_logins >= MAX_FAILED_LOGINS:
                    user.failed_logins, user.locked_until = 0, now + LOCKOUT
                outcome = InvalidCredentials()  # committed below, so the attempt is counted
            elif not user.is_active:
                outcome = InvalidCredentials()
            else:
                user.failed_logins, user.locked_until, user.last_login_at = 0, None, now
                if new_hash:
                    user.password_hash = new_hash
                await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id,
                                                                 RefreshToken.expires_at < now))
                signed_in, _ = await _issue(session, user, uuid.uuid4(), user_agent, now)
    if outcome is not None:
        raise outcome
    return signed_in


async def refresh(session: AsyncSession, token: str | None, user_agent: str | None = None) -> SignIn:
    if not token:
        raise InvalidRefresh()
    try:
        claims = security.decode_refresh_token(token)
    except security.InvalidToken as error:
        raise InvalidRefresh() from error

    signed_in: SignIn | None = None
    raced = False
    async with session.begin():
        await _begin_read_committed(session)
        now = _now()
        # Locking the row makes two refreshes with the same token take turns; the second one then
        # sees that the token was already replaced.
        row = await session.scalar(select(RefreshToken)
                                   .where(RefreshToken.token_hash == security.hash_token_id(claims.jti))
                                   .with_for_update())
        if row is None or row.user_id != claims.user_id or row.family_id != claims.family_id:
            pass
        elif row.revoked_at is not None:
            raced = row.replaced_by is not None and now - row.revoked_at <= ROTATION_GRACE
            if not raced:
                await _revoke_family(session, row.family_id, now)  # reuse of an old token: theft
        elif row.expires_at <= now:
            pass
        else:
            user = await session.get(User, row.user_id)
            if user is None or not user.is_active:
                await _revoke_family(session, row.family_id, now)
            else:
                signed_in, new_row = await _issue(session, user, row.family_id, user_agent, now)
                row.revoked_at, row.replaced_by = now, new_row.id
    if raced:
        raise RefreshRaced()
    if signed_in is None:
        raise InvalidRefresh()
    return signed_in


async def logout(session: AsyncSession, token: str | None) -> None:
    """End this sign-in (its whole token family). Unknown or expired tokens are ignored."""
    if not token:
        return
    try:
        claims = security.decode_refresh_token(token)
    except security.InvalidToken:
        return
    async with session.begin():
        await _revoke_family(session, claims.family_id, _now())


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    async with session.begin():
        user = await session.get(User, user_id)
    return user if user is not None and user.is_active else None

