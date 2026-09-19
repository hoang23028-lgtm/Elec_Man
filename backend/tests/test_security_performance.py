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
