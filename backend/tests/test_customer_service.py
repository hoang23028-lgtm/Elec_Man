import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate
from app.services import customer_service
from app.services.customer_service import (
    apply_customer_match,
    create_customer,
    list_customers,
    list_usage_purposes,
    normalize_customer_code,
    parse_customer_json,
)


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type, _compiler, **_kwargs) -> str:
    return "JSON"


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


def test_list_customers_is_paginated_sorted_and_searchable() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Customer.__table__.create(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Customer(
                    customer_code="KH002",
                    lookup_key="KH002",
                    full_name="Trần Thị B",
                    address="Khu 2",
                    electricity_route="Tuyến Bắc",
                    meter_serial="CT-002",
                    initial_reading=200,
                    usage_purpose="SINH_HOAT",
                ),
                Customer(
                    customer_code="KH001",
                    lookup_key="KH001",
                    full_name="Nguyễn Văn A",
                    address="Khu 1",
                    electricity_route="Tuyến Nam",
                    meter_serial="CT-001",
                    initial_reading=100,
                    usage_purpose="SINH_HOAT",
                ),
            ]
        )
        db.commit()

        rows, total = list_customers(db, offset=0, limit=1)
        matches, matched_total = list_customers(db, offset=0, limit=10, search="Trần")

    assert total == 2
    assert [row.customer_code for row in rows] == ["KH001"]
    assert matched_total == 1
    assert matches[0].meter_serial == "CT-002"


def test_list_usage_purposes_includes_defaults_and_database_values() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Customer.__table__.create(engine)
    with Session(engine) as db:
        db.add(
            Customer(
                customer_code="KH001",
                lookup_key="KH001",
                full_name="Nguyễn Văn A",
                address="Khu 1",
                electricity_route="Tuyến Nam",
                meter_serial="CT-001",
                initial_reading=100,
                usage_purpose="CHIẾU_SÁNG_CÔNG_CỘNG",
            )
        )
        db.commit()

        purposes = list_usage_purposes(db)

    assert "SINH_HOAT" in purposes
    assert "UB_HANH_CHINH" in purposes
    assert "CHIẾU_SÁNG_CÔNG_CỘNG" in purposes


def test_create_customer_normalizes_identifiers_and_rejects_duplicates(
    monkeypatch,
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Customer.__table__.create(engine)
    AuditLog.__table__.create(engine)
    monkeypatch.setattr(customer_service, "reconcile_confirmed_readings", lambda _: 0)
    actor = SimpleNamespace(id=uuid4())
    payload = CustomerCreate(
        customer_code=" pn3.001 ",
        full_name="Khách hàng mới",
        address="Khu 3",
        electricity_route="Tuyến 03",
        meter_serial=" ct-003 ",
        initial_reading=300,
        usage_purpose="SINH_HOAT",
    )

    with Session(engine) as db:
        created = create_customer(db, payload, actor, "127.0.0.1")
        audit = db.query(AuditLog).one()
        with pytest.raises(HTTPException) as duplicate:
            create_customer(db, payload, actor, "127.0.0.1")

    assert created.customer_code == "PN3.001"
    assert created.meter_serial == "CT-003"
    assert audit.action == "CREATE_CUSTOMER"
    assert audit.details_json["customer_code"] == "PN3.001"
    assert duplicate.value.status_code == 409
