from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def test_failed_model_load_does_not_poison_cached_version(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv(
        "SESSION_SECRET", "test-only-model-runtime-secret-at-least-32-chars"
    )
    from ai import model_runtime as runtime

    old_pipeline = object()
    monkeypatch.setattr(runtime, "_cached_ids", ("old", None))
    monkeypatch.setattr(runtime, "_cached_pipeline", old_pipeline)
    db = MagicMock()
    record = SimpleNamespace(
        id="new", version="test", model_type="reading_region_ridge"
    )
    db.scalars.return_value.all.return_value = [record]
    session = MagicMock()
    session.__enter__.return_value = db
    monkeypatch.setattr(runtime, "SessionLocal", lambda: session)
    monkeypatch.setattr(runtime, "_verified_path", lambda _: None)
    factory = MagicMock(side_effect=ValueError("invalid artifact"))
    monkeypatch.setattr(runtime, "MeterReadingPipeline", factory)

    for _ in range(2):
        with pytest.raises(ValueError, match="invalid artifact"):
            runtime.current_pipeline()
        assert runtime._cached_ids == ("old", None)
        assert runtime._cached_pipeline is old_pipeline
    assert factory.call_count == 2
    assert db.scalars.call_count == 2


def test_unchanged_registry_uses_one_query_and_keeps_loaded_pipeline(monkeypatch):
    from ai import model_runtime as runtime

    pipeline = object()
    monkeypatch.setattr(runtime, "_cached_ids", (None, None))
    monkeypatch.setattr(runtime, "_cached_pipeline", pipeline)
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.__enter__.return_value = db
    monkeypatch.setattr(runtime, "SessionLocal", lambda: session)
    factory = MagicMock(side_effect=AssertionError("must not reload"))
    monkeypatch.setattr(runtime, "MeterReadingPipeline", factory)
    assert runtime.current_pipeline() is pipeline
    db.scalars.assert_called_once()
    factory.assert_not_called()
