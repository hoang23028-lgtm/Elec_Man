import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.security.passwords import verify_password
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


def test_unknown_user_password_path_still_performs_hash_verification() -> None:
    assert verify_password(None, "not-the-dummy-password") is False


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
        )
