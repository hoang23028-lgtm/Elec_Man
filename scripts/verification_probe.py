"""Bounded HTTP checks for the disposable sandbox (never a production target)."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from statistics import quantiles
from time import perf_counter
from urllib.parse import urlparse

import httpx
from PIL import Image


def latency_summary(times):
    values = sorted(times)
    return {
        "requests": len(values),
        "p50_ms": round(quantiles(values, n=100, method="inclusive")[49], 2),
        "p95_ms": round(quantiles(values, n=100, method="inclusive")[94], 2),
        "max_ms": round(max(values), 2),
    }


def probe_application(url, password, verify, http_url=None):
    # Only called after creation/seeding; no live credentials are accepted by the CLI.
    if urlparse(url).hostname != "127.0.0.1":
        raise ValueError("Verification is restricted to the isolated loopback sandbox")
    tls = url.startswith("https://")
    report = {"tls_certificate_verified": tls, "ocr_exercised": False}
    with httpx.Client(base_url=url, verify=verify, timeout=20) as public:
        health = public.get("/api/v1/health/ready")
        assert health.status_code == 200
        assert health.headers["x-frame-options"] == "DENY"
        assert health.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in health.headers["content-security-policy"]
        if tls:
            assert "max-age=31536000" in health.headers["strict-transport-security"]
            assert public.get("/docs").status_code == 404
            # Frontend catch-all can serve /docs; API OpenAPI must be disabled.
            assert public.get("/api/v1/openapi.json").status_code == 404
            redirect = httpx.get(
                http_url + "/api/v1/health/live", follow_redirects=False
            )
            assert redirect.status_code == 308 and redirect.headers[
                "location"
            ].startswith("https://")
        assert public.get("/api/v1/results").status_code == 401
        blocked = public.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://untrusted.invalid",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in blocked.headers
        accepted = public.options(
            "/api/v1/auth/login",
            headers={"Origin": url, "Access-Control-Request-Method": "POST"},
        )
        assert accepted.headers["access-control-allow-origin"] == url
        report["security_headers_and_cors"] = "passed"

    for role in ("viewer", "admin", "super_admin"):
        with httpx.Client(
            base_url=url, verify=verify, timeout=20, headers={"Origin": url}
        ) as client:
            login = client.post(
                "/api/v1/auth/login", json={"username": role, "password": password}
            )
            assert login.status_code == 200
            cookie = login.headers["set-cookie"].lower()
            assert (
                "httponly" in cookie
                and "samesite=strict" in cookie
                and "max-age=28800" in cookie
            )
            assert ("; secure" in cookie) is tls
            csrf = login.json()["csrf_token"]
            client.headers["X-CSRF-Token"] = csrf
            assert client.get("/api/v1/results").status_code == (
                403 if role == "viewer" else 200
            )
            assert client.get("/api/v1/training").status_code == (
                200 if role == "super_admin" else 403
            )
            if role != "super_admin":
                assert client.post("/api/v1/training/runs").status_code == 403
            if role == "admin":
                del client.headers["X-CSRF-Token"]
                assert (
                    client.post(
                        "/api/v1/batches", json={"original_folder_name": "blocked"}
                    ).status_code
                    == 403
                )
                client.headers["X-CSRF-Token"] = csrf
                batch = client.post(
                    "/api/v1/batches",
                    json={"original_folder_name": "Five simultaneous uploads"},
                )
                assert batch.status_code == 201
                batch_id = batch.json()["id"]
                upload_path = f"/api/v1/batches/{batch_id}/images"
                assert (
                    client.post(
                        upload_path,
                        files={"file": ("fake.png", b"not an image", "image/png")},
                    ).status_code
                    == 422
                )

                def upload(index):
                    stream = BytesIO()
                    Image.new("RGB", (640, 480), (60 + index, 100, 150)).save(
                        stream, "PNG"
                    )
                    started = perf_counter()
                    result = client.post(
                        upload_path,
                        files={
                            "file": (
                                f"load-{index}.png",
                                stream.getvalue(),
                                "image/png",
                            )
                        },
                    )
                    assert result.status_code == 201
                    return result.json()["id"], (perf_counter() - started) * 1000

                with ThreadPoolExecutor(max_workers=5) as pool:
                    uploads = list(pool.map(upload, range(5)))
                assert len({row[0] for row in uploads}) == 5
                started = client.post(f"/api/v1/batches/{batch_id}/start")
                assert started.status_code == 200
                rows = client.get(f"/api/v1/batches/{batch_id}/images").json()
                assert len(rows) == 5
                report["five_concurrent_uploads"] = latency_summary(
                    [row[1] for row in uploads]
                )
                paths = (
                    "/api/v1/dashboard",
                    "/api/v1/dashboard/billing?month=10&year=2026",
                    "/api/v1/results?limit=10&offset=0",
                    "/api/v1/customers?limit=15&offset=0",
                    "/api/v1/batches?limit=10&offset=0",
                )

                def read(index):
                    started = perf_counter()
                    response = client.get(paths[index % len(paths)])
                    assert response.status_code == 200
                    response.json()
                    return (perf_counter() - started) * 1000

                with ThreadPoolExecutor(max_workers=10) as pool:
                    times = list(pool.map(read, range(120)))
                report["ten_concurrent_readers"] = latency_summary(times)
            assert client.post("/api/v1/auth/logout").status_code == 204
            assert client.get("/api/v1/results").status_code == 401
    report["roles_csrf_session_and_cookie_flags"] = "passed"
    with httpx.Client(base_url=url, verify=verify, timeout=20) as client:
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={
                    "username": "nonexistent_fixture",
                    "password": "Wrong-test-password-92!",
                },
            ).status_code
            for _ in range(6)
        ]
        assert statuses == [401] * 5 + [429]
        report["login_failure_rate_limit"] = statuses
    return report
