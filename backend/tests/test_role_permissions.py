import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.router import api_router
from app.core.database import get_db
from app.schemas.user import UserCreate, UserUpdate
from app.security.dependencies import (
    get_current_user,
    require_admin,
    require_csrf,
    require_super_admin,
)
from app.services import user_service


@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ADMIN", "VIEWER", "UNKNOWN"])
def test_role_permission_matrix(role):
    user = SimpleNamespace(role=role)
    for guard, allowed in [
        (require_admin, {"SUPER_ADMIN", "ADMIN"}),
        (require_super_admin, {"SUPER_ADMIN"}),
    ]:
        if role in allowed:
            assert guard(user) is user
        else:
            with pytest.raises(HTTPException) as exc:
                guard(user)
            assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["ADMIN", "VIEWER"])
def test_all_protected_routes_reject_insufficient_roles(role):
    app = FastAPI()
    app.include_router(api_router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=role)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[require_csrf] = lambda: None
    checked = 0
    with TestClient(app) as client:
        system_prefixes = ("/training", "/models", "/evaluation", "/settings", "/users", "/audit")
        operation_prefixes = ("/batches", "/customers", "/images", "/results", "/exports")
        prefixes = system_prefixes + (operation_prefixes if role == "VIEWER" else ())
        for route_path, methods in app.openapi()["paths"].items():
            if not route_path.startswith(prefixes):
                continue
            path = re.sub(r"\{[^}]+\}", str(uuid4()), route_path)
            for method in methods:
                assert client.request(method, path).status_code == 403, (method, path)
                checked += 1
    assert checked >= 10


def test_new_account_defaults_to_viewer():
    assert UserCreate(username="test-user", password="a-long-test-password").role == "VIEWER"


@pytest.mark.parametrize("role", ["ADMIN", "VIEWER"])
def test_cannot_demote_last_system_admin(role):
    user = SimpleNamespace(id=uuid4(), role="SUPER_ADMIN", is_active=True)
    actor = SimpleNamespace(id=uuid4())
    with (
        patch.object(user_service, "_get_user", return_value=user),
        patch.object(user_service, "_active_admin_count", return_value=1),
    ):
        with pytest.raises(HTTPException) as exc:
            user_service.update_user(MagicMock(), user.id, UserUpdate(role=role), actor, None)
        assert exc.value.status_code == 409


def test_role_change_revokes_sessions_and_audits_old_and_new():
    user = SimpleNamespace(id=uuid4(), role="ADMIN", is_active=True)
    actor = SimpleNamespace(id=uuid4())
    db = MagicMock()
    with (
        patch.object(user_service, "_get_user", return_value=user),
        patch.object(user_service, "_revoke_sessions") as revoke,
        patch.object(user_service, "_audit") as audit,
        patch.object(user_service.UserRow, "model_validate", return_value=user),
    ):
        user_service.update_user(db, user.id, UserUpdate(role="VIEWER"), actor, None)
    revoke.assert_called_once_with(db, user.id)
    assert audit.call_args.args[-1] == {"role": {"old": "ADMIN", "new": "VIEWER"}}
