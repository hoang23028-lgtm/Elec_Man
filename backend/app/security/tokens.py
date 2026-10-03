import hashlib
import hmac
import secrets

from app.core.config import get_settings


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def session_csrf_token(session_token: str) -> str:
    """Reproducible CSRF proof, domain-separated from session token hashes."""
    return hmac.new(
        get_settings().session_secret.encode("utf-8"),
        ("csrf:v1:" + session_token).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_token(token: str) -> str:
    return hmac.new(
        get_settings().session_secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
