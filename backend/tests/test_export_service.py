from types import SimpleNamespace

from openpyxl import load_workbook

from app.services.export_service import _excel_text, create_final_export, resolve_export_path


def test_excel_text_blocks_formula_prefixes() -> None:
    assert _excel_text("=SUM(1,2)") == "'=SUM(1,2)"


def test_export_path_rejects_unexpected_filename_without_scanning_storage() -> None:
    assert resolve_export_path("../ket-qua.xlsx") is None
    assert resolve_export_path("ket-qua.xlsx") is None


def test_final_export_contains_only_requested_columns(monkeypatch, tmp_path) -> None:
    reading = SimpleNamespace(final_customer_id="KH004", final_meter_reading="63751")
    ai_result = SimpleNamespace(final_confidence=0.8208)
    db = SimpleNamespace(execute=lambda _statement: [(reading, ai_result)])
    monkeypatch.setattr(
        "app.services.export_service.get_settings",
        lambda: SimpleNamespace(storage_root=tmp_path),
    )

    _, path = create_final_export(db)

    workbook = load_workbook(path, data_only=True)
    sheet = workbook["Chỉ số đã xác nhận"]
    rows = list(sheet.iter_rows())
    assert [cell.value for cell in rows[0]] == ["Mã khách hàng", "Số điện", "Độ tin cậy"]
    assert [cell.value for cell in rows[1]] == ["KH004", "63751", 0.8208]
    assert rows[1][2].number_format == "0.00%"
    assert sheet.auto_filter.ref == "A1:C2"
    workbook.close()
