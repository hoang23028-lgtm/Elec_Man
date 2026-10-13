from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import reviewed_image_service


def _configure_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    source = tmp_path / "original" / "meter.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"meter-image")
    monkeypatch.setattr(
        reviewed_image_service,
        "get_settings",
        lambda: SimpleNamespace(storage_root=tmp_path),
    )
    monkeypatch.setattr(
        reviewed_image_service,
        "resolve_storage_path",
        lambda _: source,
    )
    return source


def test_archive_uses_vietnamese_review_date_and_customer_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _configure_storage(monkeypatch, tmp_path)
    image = SimpleNamespace(relative_path="original/meter.jpg", reviewed_path=None)

    relative_path = reviewed_image_service.archive_reviewed_image(
        image,
        "PN2.001",
        datetime(2026, 9, 24, 18, 0, tzinfo=UTC),
    )

    assert relative_path == "reviewed/25-09-2026/PN2.001.jpg"
    assert image.reviewed_path == relative_path
    assert (tmp_path / relative_path).read_bytes() == source.read_bytes()


def test_archive_adds_suffix_instead_of_overwriting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_storage(monkeypatch, tmp_path)
    reviewed_at = datetime(2026, 9, 25, tzinfo=UTC)
    first = SimpleNamespace(relative_path="original/first.jpg", reviewed_path=None)
    second = SimpleNamespace(relative_path="original/second.jpg", reviewed_path=None)

    first_path = reviewed_image_service.archive_reviewed_image(first, "PN2.001", reviewed_at)
    second_path = reviewed_image_service.archive_reviewed_image(second, "PN2.001", reviewed_at)

    assert first_path == "reviewed/25-09-2026/PN2.001.jpg"
    assert second_path == "reviewed/25-09-2026/PN2.001_2.jpg"


def test_archive_moves_copy_when_confirmed_customer_code_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_storage(monkeypatch, tmp_path)
    reviewed_at = datetime(2026, 9, 25, tzinfo=UTC)
    image = SimpleNamespace(relative_path="original/meter.jpg", reviewed_path=None)
    old_path = reviewed_image_service.archive_reviewed_image(image, "PN2.001", reviewed_at)

    new_path = reviewed_image_service.archive_reviewed_image(image, "PN2.009", reviewed_at)

    assert not (tmp_path / old_path).exists()
    assert new_path == "reviewed/25-09-2026/PN2.009.jpg"
    assert (tmp_path / new_path).is_file()


def test_remove_reviewed_image_clears_confirmed_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_storage(monkeypatch, tmp_path)
    archived = tmp_path / "reviewed" / "25-09-2026" / "PN2.001.jpg"
    archived.parent.mkdir(parents=True)
    archived.write_bytes(b"meter-image")
    image = SimpleNamespace(
        relative_path="original/meter.jpg",
        reviewed_path="reviewed/25-09-2026/PN2.001.jpg",
    )

    previous_path = reviewed_image_service.remove_reviewed_image(image)

    assert previous_path == "reviewed/25-09-2026/PN2.001.jpg"
    assert image.reviewed_path is None
    assert not archived.exists()


def test_customer_code_cannot_escape_reviewed_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_storage(monkeypatch, tmp_path)
    image = SimpleNamespace(relative_path="original/meter.jpg", reviewed_path=None)

    relative_path = reviewed_image_service.archive_reviewed_image(
        image, "../../PN2.001", datetime(2026, 9, 25, tzinfo=UTC)
    )

    assert relative_path.startswith("reviewed/25-09-2026/")
    assert (tmp_path / relative_path).resolve().is_relative_to((tmp_path / "reviewed").resolve())


@pytest.mark.parametrize("ending", ["rollback", "close", "commit"])
def test_rename_keeps_old_copy_until_transaction_finishes(monkeypatch, tmp_path, ending):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    _configure_storage(monkeypatch, tmp_path)
    reviewed_at = datetime(2026, 9, 25, tzinfo=UTC)
    image = SimpleNamespace(relative_path="original/meter.jpg", reviewed_path=None)
    old_path = reviewed_image_service.archive_reviewed_image(image, "PN2.001", reviewed_at)
    db = Session(create_engine("sqlite://"))
    new_path = reviewed_image_service.archive_reviewed_image(image, "PN2.009", reviewed_at, db)
    assert (tmp_path / old_path).exists()
    assert (tmp_path / new_path).exists()
    getattr(db, ending)()
    assert (tmp_path / old_path).exists() == (ending != "commit")
    assert (tmp_path / new_path).exists() == (ending == "commit")
    db.close()


def test_reject_rollback_preserves_copy(monkeypatch, tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    _configure_storage(monkeypatch, tmp_path)
    image = SimpleNamespace(relative_path="original/meter.jpg", reviewed_path=None)
    path = reviewed_image_service.archive_reviewed_image(
        image, "PN2.001", datetime(2026, 9, 25, tzinfo=UTC)
    )
    with Session(create_engine("sqlite://")) as db:
        reviewed_image_service.remove_reviewed_image(image, db)
        assert (tmp_path / path).exists()
        db.rollback()
    assert (tmp_path / path).exists()


def test_savepoint_rejected_before_creating_or_deleting_files(monkeypatch, tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    _configure_storage(monkeypatch, tmp_path)
    image = SimpleNamespace(relative_path="original/meter.jpg", reviewed_path=None)
    now = datetime(2026, 9, 25, tzinfo=UTC)
    path = reviewed_image_service.archive_reviewed_image(image, "PN2.001", now)
    with Session(create_engine("sqlite://")) as db, db.begin_nested():
        with pytest.raises(RuntimeError, match="root database transaction"):
            reviewed_image_service.archive_reviewed_image(image, "PN2.009", now, db)
        with pytest.raises(RuntimeError, match="root database transaction"):
            reviewed_image_service.remove_reviewed_image(image, db)
    assert image.reviewed_path == path
    assert (tmp_path / path).is_file()
    assert len(list((tmp_path / "reviewed").rglob("*.jpg"))) == 1
