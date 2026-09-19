from fastapi import Response

from app.api.routes import audit as audit_routes
from app.api.routes import batches as batch_routes
from app.api.routes import results as result_routes


def test_batch_list_exposes_total_count(monkeypatch) -> None:
    monkeypatch.setattr(batch_routes, "count_batches", lambda _: 23)
    monkeypatch.setattr(batch_routes, "list_batches", lambda *_: [])
    response = Response()

    rows = batch_routes.list_batches_route(response, 0, 10, None, None)

    assert rows == []
    assert response.headers["X-Total-Count"] == "23"


def test_result_list_exposes_filtered_total_count(monkeypatch) -> None:
    monkeypatch.setattr(result_routes, "count_results", lambda *_: 7)
    monkeypatch.setattr(result_routes, "list_results", lambda *_: [])
    response = Response()

    rows = result_routes.get_results(
        response,
        offset=0,
        limit=12,
        image_status="CONFIRMED",
        search="KH004",
        db=None,
        _=None,
    )

    assert rows == []
    assert response.headers["X-Total-Count"] == "7"


def test_audit_list_exposes_filtered_total_count(monkeypatch) -> None:
    monkeypatch.setattr(audit_routes, "count_audit_logs", lambda *_: 41)
    monkeypatch.setattr(audit_routes, "list_audit_logs", lambda *_: [])
    response = Response()

    rows = audit_routes.get_audit_logs(
        response,
        offset=0,
        limit=10,
        action="confirm_result",
        db=None,
        _=None,
    )

    assert rows == []
    assert response.headers["X-Total-Count"] == "41"
