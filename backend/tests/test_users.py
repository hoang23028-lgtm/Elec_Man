import pytest
from pydantic import ValidationError

from app.schemas.auth import RegistrationRequest
from app.schemas.user import PasswordUpdate, UserCreate, UserUpdate


def test_user_create_accepts_safe_username_and_long_password() -> None:
    payload = UserCreate(username="admin.operator_2", password="a-secure-password")
    assert payload.username == "admin.operator_2"
    assert payload.is_active is True


@pytest.mark.parametrize("username", ["ab", "admin user", "admin@company", "quản-trị"])
def test_user_create_rejects_invalid_username(username: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(username=username, password="a-secure-password")


def test_password_requires_at_least_twelve_characters() -> None:
    with pytest.raises(ValidationError):
        PasswordUpdate(new_password="short")


def test_user_update_requires_at_least_one_change() -> None:
    with pytest.raises(ValidationError):
        UserUpdate()


def test_registration_requires_safe_username_and_strong_password() -> None:
    payload = RegistrationRequest(username=" pending.user ", password="a-secure-password")

    assert payload.username == "pending.user"


@pytest.mark.parametrize("password", ["short", "", "12345678901"])
def test_registration_rejects_short_password(password: str) -> None:
    with pytest.raises(ValidationError):
        RegistrationRequest(username="pending.user", password=password)
