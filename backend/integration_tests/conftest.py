import os

import pytest

if os.environ.get("ELEC_MAN_INTEGRATION") != "1":
    pytest.skip("Use scripts/test-integration.py for an isolated database", allow_module_level=True)

from sqlalchemy.engine import make_url  # noqa: E402

url = make_url(os.environ["DATABASE_URL"])
if url.host != "127.0.0.1" or url.database != "elec_man_integration":
    raise RuntimeError("Integration tests require the isolated loopback database")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402

PASSWORD = "Integration-test-only-92!"


@pytest.fixture(scope="session", autouse=True)
def accounts():
    with SessionLocal() as db:
        for role in ("VIEWER", "ADMIN", "SUPER_ADMIN"):
            db.add(User(username=role.lower(), role=role, password_hash=hash_password(PASSWORD)))
        db.commit()


@pytest.fixture
def login():
    clients = []

    def create(role):
        client = TestClient(app)
        clients.append(client)
        response = client.post(
            "/api/v1/auth/login", json={"username": role.lower(), "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=strict" in response.headers["set-cookie"].lower()
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return client

    yield create
    for client in clients:
        client.close()
