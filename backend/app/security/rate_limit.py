import time
from collections import deque
from threading import Lock


class LoginRateLimiter:
    """Small in-memory limiter suitable for the single-server deployment."""

    def __init__(
        self, attempts: int = 5, window_seconds: int = 900, max_keys: int = 10_000
    ) -> None:
        self.attempts = attempts
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._attempts: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            records = self._attempts.get(key)
            if records is None:
                return True
            while records and records[0] <= now - self.window_seconds:
                records.popleft()
            if not records:
                self._attempts.pop(key, None)
                return True
            return len(records) < self.attempts

    def record_failure(self, key: str) -> None:
        with self._lock:
            if key not in self._attempts and len(self._attempts) >= self.max_keys:
                self._attempts.pop(next(iter(self._attempts)))
            self._attempts.setdefault(key, deque()).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


login_account_rate_limiter = LoginRateLimiter()
login_ip_rate_limiter = LoginRateLimiter(attempts=30)
