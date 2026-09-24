from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services import storage_service


def test_original_upload_name_removes_client_path() -> None:
    assert storage_service._safe_original_name(r"C:\fakepath\meter.jpg") == "meter.jpg"


@pytest.mark.parametrize("filename", ["meter.jpg:payload.exe", "meter\n.jpg", ".."])
def test_original_upload_name_rejects_unsafe_values(filename: str) -> None:
    with pytest.raises(HTTPException):
        storage_service._safe_original_name(filename)


def test_storage_path_cannot_escape_configured_root(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "storage"
    root.mkdir()
    outside = tmp_path / "secret.jpg"
    outside.write_bytes(b"not-an-image")
    monkeypatch.setattr(
        storage_service,
        "get_settings",
        lambda: type("Settings", (), {"storage_root": root})(),
    )

    with pytest.raises(HTTPException) as error:
        storage_service.resolve_storage_path("../secret.jpg")

    assert error.value.status_code == 404
