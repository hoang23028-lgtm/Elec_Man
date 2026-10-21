import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("runtime_report", SCRIPTS / "copy_runtime_report.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@pytest.fixture
def report_source(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "ROOT", tmp_path)
    monkeypatch.setattr(runtime, "inventory", lambda _: {"worker": {"Id": "fixture"}})
    value = {"scope": "saved_labels_diagnostic_not_independent_holdout", "database_mutated": False}
    monkeypatch.setattr(runtime, "docker", lambda *a, **kw: json.dumps(value))
    return value


def test_copy_report_preserves_scope_and_never_overwrites(report_source, tmp_path):
    path = runtime.copy_report("fixture", "encoder-test.json")
    assert path.parent == tmp_path / ".codex-tmp"
    assert json.loads(path.read_text(encoding="utf-8")) == report_source
    with pytest.raises(FileExistsError):
        runtime.copy_report("fixture", "encoder-test.json")


@pytest.mark.parametrize(
    "name", ["../encoder.json", "secret.json", "encoder/X.json", "encoder.json;ls"]
)
def test_invalid_report_name_does_not_access_docker(monkeypatch, name):
    monkeypatch.setattr(runtime, "inventory", lambda _: pytest.fail("No Docker access"))
    with pytest.raises(ValueError):
        runtime.copy_report("fixture", name)


@pytest.mark.parametrize(
    "raw",
    ["[]", "null", '{"scope":"other"}', '{"database_mutated":true}', "x" * (5 * 1024**2 + 1)],
    ids=["list", "null", "scope", "mutation", "oversize"],
)
def test_invalid_report_rejected_without_writing(report_source, monkeypatch, raw, tmp_path):
    monkeypatch.setattr(runtime, "docker", lambda *a, **kw: raw)
    with pytest.raises(ValueError):
        runtime.copy_report("fixture", "encoder-test.json")
    assert not (tmp_path / ".codex-tmp").exists()


def test_invalid_project_does_not_access_docker(monkeypatch):
    monkeypatch.setattr(runtime, "inventory", lambda _: pytest.fail("No Docker access"))
    with pytest.raises(ValueError):
        runtime.copy_report("../fixture", "encoder-test.json")
