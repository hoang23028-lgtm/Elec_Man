import pytest
from fastapi import HTTPException, Response

from app.api.pagination import validate_pagination
from app.api.routes import audit as audit_routes
from app.api.routes import batches as batch_routes
from app.api.routes import results as result_routes


@pytest.mark.parametrize("offset,limit", [(-1, 10), (0, 0), (0, 101)])
def test_invalid_pagination_is_rejected(offset: int, limit: int) -> None:
    with pytest.raises(HTTPException) as error:
        validate_pagination(offset, limit)

    assert error.value.status_code == 422


def test_batch_list_exposes_total_count(monkeypatch) -> None:
    monkeypatch.setattr(batch_routes, "list_batches", lambda *_: ([], 23))
    response = Response()

    rows = batch_routes.list_batches_route(response, 0, 10, None, None)

    assert rows == []
    assert response.headers["X-Total-Count"] == "23"


def test_result_list_exposes_filtered_total_count(monkeypatch) -> None:
    monkeypatch.setattr(result_routes, "list_results", lambda *_: ([], 7))
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
    monkeypatch.setattr(audit_routes, "list_audit_logs", lambda *_: ([], 41))
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
