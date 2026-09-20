from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()
_dummy_password_hash = _hasher.hash("dummy-password-used-only-to-equalize-login-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _dummy_password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False
