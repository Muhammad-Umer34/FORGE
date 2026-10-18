"""Unit tests for passwords and sign-in tokens (D-176, D-177). No database, no network."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.core import security
from backend.core.config import settings

ACCESS_SECRET = "a" * 48
REFRESH_SECRET = "r" * 48


@pytest.fixture(autouse=True)
def fixed_secrets(monkeypatch):
    monkeypatch.setattr(settings, "JWT_ACCESS_SECRET", ACCESS_SECRET)
    monkeypatch.setattr(settings, "JWT_REFRESH_SECRET", REFRESH_SECRET)


def test_password_hash_is_argon2id_and_verifies():
    hashed = security.hash_password("correct horse battery")
    assert hashed.startswith("$argon2id$")
    assert security.verify_password("correct horse battery", hashed) == (True, None)
    assert security.verify_password("wrong password", hashed)[0] is False


def test_same_password_hashes_differently():
    assert security.hash_password("same password") != security.hash_password("same password")


def test_unknown_user_and_malformed_hash_never_verify():
    assert security.verify_password("anything", None) == (False, None)
    assert security.verify_password("anything", "not-a-hash") == (False, None)


def test_access_token_round_trip():
    uid = uuid.uuid4()
    token, expires = security.create_access_token(uid)
    assert security.decode_access_token(token) == uid
    assert security.decode_access(token).email_verified is False
    verified, _ = security.create_access_token(uid, email_verified=True)
    assert security.decode_access(verified) == security.AccessClaims(uid, True)
    assert timedelta(minutes=14) < expires - datetime.now(timezone.utc) <= timedelta(minutes=15)


def test_expired_access_token_is_refused():
    token, _ = security.create_access_token(uuid.uuid4(), now=datetime.now(timezone.utc) - timedelta(hours=1))
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(token)


def test_tampered_or_foreign_tokens_are_refused():
    uid = uuid.uuid4()
    token, _ = security.create_access_token(uid)
    header, payload, signature = token.split(".")
    flipped = signature[:-2] + ("AA" if signature[-2:] != "AA" else "BB")
    forged = jwt.encode({"sub": str(uid), "type": "access", "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
                         "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                        "some-other-secret-that-is-long-enough-123", algorithm="HS256")
    unsigned = jwt.encode({"sub": str(uid), "type": "access"}, None, algorithm="none")
    for bad in (f"{header}.{payload}.{flipped}", forged, unsigned, "not.a.token", ""):
        with pytest.raises(security.InvalidToken):
            security.decode_access_token(bad)


def test_wrong_issuer_or_audience_is_refused():
    now = datetime.now(timezone.utc)
    base = {"sub": str(uuid.uuid4()), "type": "access", "iat": now, "exp": now + timedelta(minutes=5)}
    for claims in ({**base, "iss": "someone-else", "aud": settings.JWT_AUDIENCE},
                   {**base, "iss": settings.JWT_ISSUER, "aud": "another-app"}):
        token = jwt.encode(claims, ACCESS_SECRET, algorithm="HS256")
        with pytest.raises(security.InvalidToken):
            security.decode_access_token(token)


def test_refresh_and_access_tokens_cannot_be_swapped():
    uid = uuid.uuid4()
    refresh, _, _ = security.create_refresh_token(uid, uuid.uuid4())
    access, _ = security.create_access_token(uid)
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(refresh)
    with pytest.raises(security.InvalidToken):
        security.decode_refresh_token(access)


def test_refresh_token_carries_family_and_unique_id():
    uid, family = uuid.uuid4(), uuid.uuid4()
    token_a, jti_a, _ = security.create_refresh_token(uid, family)
    token_b, jti_b, _ = security.create_refresh_token(uid, family)
    claims = security.decode_refresh_token(token_a)
    assert (claims.user_id, claims.family_id, claims.jti) == (uid, family, jti_a)
    assert jti_a != jti_b and token_a != token_b
    assert security.hash_token_id(jti_a) != jti_a and len(security.hash_token_id(jti_a)) == 64


def test_missing_or_short_secret_is_an_error(monkeypatch):
    monkeypatch.setattr(settings, "JWT_ACCESS_SECRET", "short")
    with pytest.raises(RuntimeError):
        security.create_access_token(uuid.uuid4())


def test_emails_contain_the_link_and_escape_names():
    from backend.services import mailer

    mail = mailer.verification_email("a@example.com", "<Ayesha>", "http://localhost:3000/verify-email?token=abc")
    assert "http://localhost:3000/verify-email?token=abc" in mail.text
    assert "&lt;Ayesha&gt;" in mail.html and "<Ayesha>" not in mail.html
    reset = mailer.reset_email("a@example.com", "Ayesha", "http://localhost:3000/reset-password?token=xyz")
    assert reset.subject == "Reset your FORGE password" and "30 minutes" in reset.text
