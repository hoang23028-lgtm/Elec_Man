from app.services.performance_profile import summarize_timings


def test_profiles_separate_manual_and_automatic_without_leaking_raw_values():
    result = summarize_timings(
        [
            (
                {"read_digits": 20, "customer_code": "PRIVATE", "preprocess": float("nan")},
                False,
                {"ppocr": {"rpc_ms": 15, "value": "PRIVATE"}},
            ),
            ({"read_digits": 40}, False, {}),
            ({"read_digits": 5, "crop": True}, True, {}),
        ]
    )
    assert result["automatic"]["read_digits"]["samples"] == 2
    assert result["manual"]["read_digits"]["p50_ms"] == 5
    assert "PRIVATE" not in str(result) and "preprocess" not in result["automatic"]
    assert "crop" not in result["manual"]


def test_profile_rejects_invalid_and_unknown_timing_fields():
    assert summarize_timings(
        [(None, False, "bad"), ({"decode": -1, "scene_ocr": float("inf"), "password": 1}, None, [])]
    ) == {"automatic": {}, "manual": {}}
