from fastapi.testclient import TestClient

from app.api.routes import dashboard as dashboard_routes
from app.main import app


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "backend", "database": None}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_dashboard_aggregate_is_public(monkeypatch) -> None:
    payload = {
        "batches": 2,
        "images": 8,
        "jobs": {"PENDING": 1, "PROCESSING": 0, "COMPLETED": 7, "FAILED": 0, "CANCELLED": 0},
    }
    monkeypatch.setattr(dashboard_routes, "statistics", lambda _: payload)

    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert response.json() == payload
