"""Shared test setup: the cost and abuse limits (D-189 - D-194) are counted in the test database
and would build up across tests and runs, so every test starts with very high limits. The tests in
test_limits.py lower the one they check."""
import pytest

from backend.core.config import settings

_LIMITS = [
    "LIMIT_REQUESTS_PER_USER_DAY", "LIMIT_REQUESTS_PER_DAY", "LIMIT_SIGNUPS_PER_IP_HOUR", "LIMIT_SIGNUPS_PER_IP_DAY",
    "LIMIT_SIGNUPS_PER_DAY", "LIMIT_FORGOT_PER_IP_HOUR", "LIMIT_EMAILS_PER_DAY", "LIMIT_LOGIN_FAILS_PER_ACCOUNT_HOUR",
    "LIMIT_LOGIN_FAILS_PER_IP", "LIMIT_WEBSITE_READS_PER_USER_DAY", "LIMIT_IMAGE_READS_PER_USER_HOUR",
]


@pytest.fixture(autouse=True)
def generous_limits(monkeypatch):
    for name in _LIMITS:
        monkeypatch.setattr(settings, name, 1_000_000)
