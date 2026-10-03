from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.security.dependencies import AuthContext, get_auth_context, require_admin, require_csrf
from app.security.tokens import generate_token, hash_token, session_csrf_token


def _request(cookie, csrf=None):
    headers = [(b"cookie", f"{get_settings().session_cookie_name}={cookie}".encode())]
    if csrf is not None:
        headers.append((b"x-csrf-token", csrf.encode()))
    return Request({"type": "http", "headers": headers})


def _context():
    return AuthContext(
        session=SimpleNamespace(
            csrf_token_hash=hash_token("legacy-csrf"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            revoked_at=None,
        ),
        user=SimpleNamespace(is_active=True, deleted_at=None, username="admin", role="ADMIN"),
    )


def test_restore_proof_is_stable_session_bound_and_domain_separated():
    token = generate_token()
    proof = session_csrf_token(token)
    assert proof == session_csrf_token(token)
    assert proof != token and proof != hash_token(token)
    assert proof != session_csrf_token(generate_token())


def test_restored_and_legacy_csrf_work_without_rotating_other_tabs():
    context = _context()
    for proof in ["legacy-csrf", session_csrf_token("session-one")]:
        assert require_csrf(_request("session-one", proof), context) is context
    assert context.session.csrf_token_hash == hash_token("legacy-csrf")


def test_admin_dependency_denies_non_admin_accounts():
    user = SimpleNamespace(role="VIEWER")
    with pytest.raises(HTTPException) as exc:
        require_admin(user)
    assert exc.value.status_code == 403
    admin = SimpleNamespace(role="ADMIN")
    assert require_admin(admin) is admin


@pytest.mark.parametrize(
    "proof", [None, "invalid", session_csrf_token("different-session"), "session-one"]
)
def test_invalid_or_missing_proof_cannot_mutate(proof):
    with pytest.raises(HTTPException) as exc:
        require_csrf(_request("session-one", proof), _context())
    assert exc.value.status_code == 403


@pytest.mark.parametrize("invalid", ["expired", "revoked", "inactive", "deleted", "unknown"])
def test_restore_rejects_invalid_sessions(invalid):
    context = _context()
    if invalid == "expired":
        context.session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    if invalid == "revoked":
        context.session.revoked_at = datetime.now(UTC)
    if invalid == "inactive":
        context.user.is_active = False
    if invalid == "deleted":
        context.user.deleted_at = datetime.now(UTC)
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = (
        None if invalid == "unknown" else (context.session, context.user)
    )
    with pytest.raises(HTTPException) as exc:
        get_auth_context(_request("session-one"), db)
    assert exc.value.status_code == 401
    assert hash_token("session-one") in db.execute.call_args.args[0].compile().params.values()


def test_restore_route_authenticates_and_never_returns_cookie_or_caches_token():
    context = _context()
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = (context.session, context.user)
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/auth/session", cookies={get_settings().session_cookie_name: "session-one"}
            )
            assert response.status_code == 200
            assert response.json()["csrf_token"] == session_csrf_token("session-one")
            assert response.json()["username"] == "admin"
            assert response.json()["role"] == "ADMIN"
            assert "session-one" not in response.text
            assert response.headers["cache-control"] == "no-store"
            assert "set-cookie" not in response.headers
            assert client.get("/api/v1/auth/session").status_code == 401
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)
