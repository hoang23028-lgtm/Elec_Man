from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import Request, Response
from pydantic import ValidationError

from app.api.routes import auth as auth_routes
from app.core.config import Settings
from app.schemas.auth import LoginRequest
from app.security import tokens
from app.security.passwords import hash_password, verify_password
from app.security.rate_limit import LoginRateLimiter


def test_rate_limiter_does_not_allocate_for_clean_keys() -> None:
    limiter = LoginRateLimiter(attempts=2, window_seconds=60)

    assert limiter.allowed("new-key") is True
    assert limiter._attempts == {}


def test_rate_limiter_tracks_failures_and_reset_releases_key() -> None:
    limiter = LoginRateLimiter(attempts=2, window_seconds=60)
    limiter.record_failure("client")
    limiter.record_failure("client")

    assert limiter.allowed("client") is False
    limiter.reset("client")
    assert limiter.allowed("client") is True
    assert limiter._attempts == {}


def test_rate_limiter_bounds_untrusted_key_storage() -> None:
    limiter = LoginRateLimiter(attempts=2, window_seconds=60, max_keys=2)
    limiter.record_failure("first")
    limiter.record_failure("second")
    limiter.record_failure("third")

    assert len(limiter._attempts) == 2
    assert "first" not in limiter._attempts
    assert set(limiter._attempts) == {"second", "third"}


def test_unknown_user_password_path_still_performs_hash_verification() -> None:
    assert verify_password(None, "not-the-dummy-password") is False


def test_passwords_use_argon2id() -> None:
    password_hash = hash_password("a-long-and-unique-password")
    assert password_hash.startswith("$argon2id$")
    assert verify_password(password_hash, "a-long-and-unique-password") is True


def test_session_token_hash_is_keyed_by_server_secret(monkeypatch) -> None:
    class TestSettings:
        session_secret = "first-test-secret-with-at-least-32-characters"

    settings = TestSettings()
    monkeypatch.setattr(tokens, "get_settings", lambda: settings)
    first = tokens.hash_token("same-session-token")
    settings.session_secret = "second-test-secret-with-at-least-32-characters"
    second = tokens.hash_token("same-session-token")

    assert first != second
    assert len(first) == 64


def test_production_login_cookie_has_required_security_attributes(monkeypatch) -> None:
    expires_at = datetime.now(UTC) + timedelta(hours=8)
    monkeypatch.setattr(
        auth_routes,
        "authenticate",
        lambda *_: ("session-token", "csrf-token", expires_at),
    )
    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: SimpleNamespace(
            session_cookie_name="ema_session", app_env="production", session_ttl_hours=8
        ),
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "scheme": "https",
            "server": ("testserver", 443),
        }
    )
    response = Response()

    auth_routes.login(
        LoginRequest(username="cookie-test-user", password="valid-test-password"),
        request,
        response,
        db=object(),
    )

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Max-Age=28800" in cookie


@pytest.mark.parametrize(
    ("database_url", "session_secret", "allowed_hosts"),
    [
        (
            "postgresql+psycopg://app:change-me-before-deployment@db/app",
            "a-secure-session-secret-with-more-than-32-characters",
            "example.com",
        ),
        (
            "postgresql+psycopg://app:strong-password@db/app",
            "replace-with-a-64-character-random-secret-before-production",
            "example.com",
        ),
        (
            "postgresql+psycopg://app:strong-password@db/app",
            "a-secure-session-secret-with-more-than-32-characters",
            "*",
        ),
    ],
)
def test_production_rejects_insecure_defaults(
    database_url: str, session_secret: str, allowed_hosts: str
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            database_url=database_url,
            session_secret=session_secret,
            allowed_hosts=allowed_hosts,
            enforce_https=True,
            frontend_origin="https://example.com",
        )


@pytest.mark.parametrize(
    ("enforce_https", "frontend_origin"),
    [(False, "https://example.com"), (True, "http://example.com")],
)
def test_production_requires_https(enforce_https: bool, frontend_origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://app:strong-password@db/app",
            session_secret="a-secure-session-secret-with-more-than-32-characters",
            allowed_hosts="example.com",
            enforce_https=enforce_https,
            frontend_origin=frontend_origin,
        )
