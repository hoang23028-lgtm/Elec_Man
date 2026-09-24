import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.customer_service import (
    apply_customer_match,
    normalize_customer_code,
    parse_customer_json,
)


def test_normalize_customer_code_ignores_formatting() -> None:
    assert normalize_customer_code(" pn2.001 ") == "PN2001"
    assert normalize_customer_code("PN2-001") == "PN2001"


def test_parse_customer_json_accepts_supplied_shape() -> None:
    content = json.dumps(
        [
            {
                "ma_khach_hang": "PN2.001",
                "ho_ten": "Nguyễn Văn A",
                "dia_chi": "Khu 1",
                "tuyen_dien": "Tuyến 02",
                "so_seri_cong_to": "CT-2026-001",
                "chi_so_khoi_tao": 13836,
                "muc_dich_su_dung": "SINH_HOAT",
            }
        ],
        ensure_ascii=False,
    ).encode()

    rows = parse_customer_json(content)

    assert rows[0].customer_code == "PN2.001"
    assert rows[0].initial_reading == 13836


def test_parse_customer_json_rejects_negative_reading() -> None:
    content = json.dumps(
        [
            {
                "ma_khach_hang": "A01",
                "ho_ten": "A",
                "dia_chi": "A",
                "tuyen_dien": "A",
                "so_seri_cong_to": "S01",
                "chi_so_khoi_tao": -1,
                "muc_dich_su_dung": "A",
            }
        ]
    ).encode()
    with pytest.raises(ValueError, match="không hợp lệ"):
        parse_customer_json(content)


def test_apply_customer_match_uses_canonical_code() -> None:
    customer_id = uuid4()
    customer = SimpleNamespace(id=customer_id, customer_code="PN2.001")
    reading = SimpleNamespace(
        matched_customer_id=None,
        customer_match_status="NOT_CHECKED",
        final_customer_id="PN2001",
    )

    apply_customer_match(reading, customer)

    assert reading.matched_customer_id == customer_id
    assert reading.customer_match_status == "MATCHED"
    assert reading.final_customer_id == "PN2.001"
