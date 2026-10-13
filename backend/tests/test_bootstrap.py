import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.scripts import init_admin
from app.security.passwords import verify_password

SPEC = importlib.util.spec_from_file_location(
    "bootstrap", Path(__file__).resolve().parents[2] / "scripts" / "bootstrap.py"
)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


@pytest.fixture
def workspace(tmp_path):
    source = Path(__file__).resolve().parents[2] / ".env.example"
    (tmp_path / ".env.example").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_private_config_matches_database_password_and_is_not_overwritten(workspace):
    assert bootstrap.create_environment(workspace, ".env", 8088)
    original = (workspace / ".env").read_text(encoding="utf-8")
    env = dict(
        line.split("=", 1)
        for line in original.splitlines()
        if "=" in line and not line.startswith("#")
    )
    assert len(env["POSTGRES_PASSWORD"]) == 64
    assert len(env["SESSION_SECRET"]) == 96
    assert f":{env['POSTGRES_PASSWORD']}@" in env["DATABASE_URL"]
    assert env["FRONTEND_ORIGIN"] == "http://localhost:8088"
    assert env["ADMIN_INITIAL_PASSWORD"] == ""
    assert not bootstrap.create_environment(workspace, ".env", 80)
    assert (workspace / ".env").read_text(encoding="utf-8") == original


@pytest.mark.parametrize("filename", [".env.example", "../.env", "/tmp/.env", "public.env"])
def test_config_rejects_public_or_escaping_paths(workspace, filename):
    with pytest.raises(ValueError):
        bootstrap.create_environment(workspace, filename, 80)


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_config_rejects_invalid_port(workspace, port):
    with pytest.raises(ValueError):
        bootstrap.create_environment(workspace, ".env", port)


def test_config_rejects_empty_existing_file(workspace):
    (workspace / ".env").touch()
    with pytest.raises(ValueError):
        bootstrap.create_environment(workspace, ".env", 80)


@pytest.fixture
def admin_database(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[User.__table__])
    factory = sessionmaker(engine)
    monkeypatch.setattr(init_admin, "SessionLocal", factory)
    monkeypatch.setattr(
        init_admin.get_settings(), "admin_initial_password", "fixture-only-password-123"
    )
    yield factory
    engine.dispose()


def test_initializer_creates_once_without_promoting_registered_viewer(admin_database, monkeypatch):
    with admin_database() as db:
        db.add(User(username="viewer", password_hash="unused", role="VIEWER", is_active=False))
        db.commit()
    monkeypatch.setattr("sys.argv", ["init_admin", "--check"])
    assert init_admin.main() == 1
    monkeypatch.setattr("sys.argv", ["init_admin", "--username", "admin"])
    assert init_admin.main() == 0
    assert init_admin.main() == 0
    with admin_database() as db:
        users = db.scalars(select(User).order_by(User.username)).all()
        assert len(users) == 2
        assert users[0].role == "SUPER_ADMIN"
        assert verify_password(users[0].password_hash, "fixture-only-password-123")
        assert users[1].role == "VIEWER"
    monkeypatch.setattr("sys.argv", ["init_admin", "--check"])
    assert init_admin.main() == 0


def test_initializer_does_not_promote_username_collision(admin_database, monkeypatch):
    with admin_database() as db:
        db.add(User(username="admin", password_hash="unused", role="VIEWER"))
        db.commit()
    monkeypatch.setattr("sys.argv", ["init_admin", "--username", "admin"])
    assert init_admin.main() == 2


def test_locked_system_admin_cannot_be_bypassed(admin_database, monkeypatch):
    with admin_database() as db:
        db.add(User(username="locked", password_hash="unused", role="SUPER_ADMIN", is_active=False))
        db.commit()
    monkeypatch.setattr("sys.argv", ["init_admin", "--check"])
    assert init_admin.main() == 0
