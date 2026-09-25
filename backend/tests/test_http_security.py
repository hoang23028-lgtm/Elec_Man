from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from app.security.dependencies import get_auth_context, get_current_user
from app.security.middleware import SecurityMiddleware


def _dependency_calls(route: APIRoute) -> Iterator[object]:
    pending = list(route.dependant.dependencies)
    while pending:
        dependency = pending.pop()
        yield dependency.call
        pending.extend(dependency.dependencies)


def test_every_non_public_api_route_requires_authentication() -> None:
    public = {
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/register"),
        ("GET", "/api/v1/dashboard"),
        ("GET", "/api/v1/dashboard/billing"),
        ("GET", "/api/v1/health/live"),
        ("GET", "/api/v1/health/ready"),
    }
    failures: list[str] = []
    for base_route in app.routes:
        if not isinstance(base_route, APIRoute):
            continue
        calls = set(_dependency_calls(base_route))
        for method in base_route.methods:
            if method in {"HEAD", "OPTIONS"} or (method, base_route.path) in public:
                continue
            if get_auth_context not in calls and get_current_user not in calls:
                failures.append(f"{method} {base_route.path}")
    assert failures == []


def test_unhandled_errors_return_safe_message_and_request_id() -> None:
    test_app = FastAPI()
    test_app.add_middleware(SecurityMiddleware)

    @test_app.get("/failure")
    def failure() -> None:
        raise RuntimeError("database password and internal path must not be exposed")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/failure")

    assert response.status_code == 500
    assert response.json()["detail"] == "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau."
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "password" not in response.text


def test_cors_does_not_allow_unconfigured_origin() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert "access-control-allow-origin" not in response.headers
