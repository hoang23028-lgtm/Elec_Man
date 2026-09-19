from app.services.job_service import should_auto_confirm


def test_auto_confirm_requires_confidence_strictly_above_threshold() -> None:
    result = {
        "customer_id_ai": "KH004",
        "meter_reading_ai": "63751.3",
        "final_confidence": 0.9,
    }

    assert should_auto_confirm(result, 0.9) is False
    result["final_confidence"] = 0.9001
    assert should_auto_confirm(result, 0.9) is True


def test_auto_confirm_requires_both_extracted_values() -> None:
    result = {
        "customer_id_ai": "KH004",
        "meter_reading_ai": None,
        "final_confidence": 0.99,
    }

    assert should_auto_confirm(result, 0.9) is False


def test_auto_confirm_requires_numeric_meter_reading() -> None:
    result = {
        "customer_id_ai": "KH004",
        "meter_reading_ai": "không đọc được",
        "final_confidence": 0.99,
    }

    assert should_auto_confirm(result, 0.9) is False
