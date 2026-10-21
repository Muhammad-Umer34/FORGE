# D:\FYP\FORGE-1\backend\core\security.py
"""
Passwords and sign-in tokens (D-176, D-177). Pure functions, no database.

- Passwords: Argon2id through pwdlib (OWASP's first choice). Hashing is slow on purpose, so the
  service runs it in a worker thread.
- Access token: a JWT signed with JWT_ACCESS_SECRET, valid ACCESS_TOKEN_MINUTES. Sent by the
  frontend as "Authorization: Bearer ...". Never stored on our side.
- Refresh token: a JWT signed with a different secret, valid REFRESH_TOKEN_DAYS, carried in an
  HttpOnly cookie. Its random id (jti) is stored hashed, so it can be rotated and revoked.
Every decode checks the signature, the algorithm (HS256 only), expiry, issuer, audience and type,
so a refresh token can never be used as an access token or the other way round.
"""
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from backend.core.config import settings

ALGORITHM = "HS256"
_MIN_SECRET_LENGTH = 32
_hasher = PasswordHash.recommended()  # Argon2id
# Checked against when the email is unknown, so a wrong email takes as long as a wrong password
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


class InvalidToken(Exception):
    """The token is missing, expired, forged or of the wrong type."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """(matches, new_hash). new_hash is set when the stored hash uses outdated settings."""
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False, None
    try:
        return _hasher.verify_and_update(password, password_hash)
    except Exception:  # malformed or unknown hash format
        return False, None


def hash_token_id(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def _secret(kind: str) -> str:
    value = settings.JWT_ACCESS_SECRET if kind == "access" else settings.JWT_REFRESH_SECRET
    if len(value) < _MIN_SECRET_LENGTH:
        raise RuntimeError(f"JWT_{kind.upper()}_SECRET is missing or shorter than {_MIN_SECRET_LENGTH} characters in .env")
    return value


def _encode(kind: str, claims: dict, lifetime: timedelta, now: datetime | None) -> tuple[str, datetime]:
    issued = now or datetime.now(timezone.utc)
    expires = issued + lifetime
    payload = {**claims, "type": kind, "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
               "iat": issued, "exp": expires}
    return jwt.encode(payload, _secret(kind), algorithm=ALGORITHM), expires


def _decode(kind: str, token: str) -> dict:
    try:
        claims = jwt.decode(
            token, _secret(kind), algorithms=[ALGORITHM], audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER, options={"require": ["exp", "iat", "sub", "type", "iss", "aud"]},
        )
    except jwt.PyJWTError as error:
        raise InvalidToken(str(error)) from error
    if claims.get("type") != kind:
        raise InvalidToken("wrong token type")
    return claims


def create_access_token(user_id: uuid.UUID, now: datetime | None = None, email_verified: bool = False) -> tuple[str, datetime]:
    """`ev` says whether the email was verified when the token was made; it changes at the next refresh."""
    return _encode("access", {"sub": str(user_id), "ev": bool(email_verified)},
                   timedelta(minutes=settings.ACCESS_TOKEN_MINUTES), now)


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    email_verified: bool


def decode_access(token: str) -> AccessClaims:
    claims = _decode("access", token)
    try:
        return AccessClaims(uuid.UUID(claims["sub"]), claims.get("ev") is True)
    except ValueError as error:
        raise InvalidToken("bad subject") from error


@dataclass(frozen=True)
class RefreshClaims:
    user_id: uuid.UUID
    jti: str
    family_id: uuid.UUID


def create_refresh_token(user_id: uuid.UUID, family_id: uuid.UUID,
                         now: datetime | None = None) -> tuple[str, str, datetime]:
    """(token, jti, expires_at). The caller stores hash_token_id(jti), never the token."""
    jti = secrets.token_urlsafe(32)
    token, expires = _encode("refresh", {"sub": str(user_id), "jti": jti, "fam": str(family_id)},
                             timedelta(days=settings.REFRESH_TOKEN_DAYS), now)
    return token, jti, expires


def decode_refresh_token(token: str) -> RefreshClaims:
    claims = _decode("refresh", token)
    try:
        return RefreshClaims(uuid.UUID(claims["sub"]), str(claims["jti"]), uuid.UUID(claims["fam"]))
    except (KeyError, ValueError) as error:
        raise InvalidToken("bad refresh claims") from error
