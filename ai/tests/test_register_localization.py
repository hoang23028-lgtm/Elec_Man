from ai.pipeline.localization import _ocr_reading_candidate
from ai.pipeline.scene_ocr import TextLine


def line(text, x, y, width=140, height=30, confidence=0.99):
    return TextLine(
        ((x, y), (x + width, y), (x + width, y + height), (x, y + height)),
        text,
        confidence,
    )


def test_register_unit_beats_confident_year_and_stamp():
    result = _ocr_reading_candidate(
        [
            line("2011", 400, 600),
            line("06909", 20, 450),
            line("9510?RkWh", 150, 420, 310, 45, 0.8),
        ],
        720,
        1280,
    )
    assert result is not None
    assert result[0][0] > 100 and result[0][1] < 430
    assert result[1] < 0.88


def test_separate_unit_prefers_register_to_stamp_below_unit():
    result = _ocr_reading_candidate(
        [
            line("01338", 230, 550),
            line("001779", 430, 580, 55, 17),
            line("kWh", 400, 540, 75, 30),
        ],
        720,
        1280,
    )
    assert result is not None and result[0][0] < 230


def test_nameplate_kwh_is_not_register():
    assert (
        _ocr_reading_candidate(
            [
                line("1000rev/kWh", 20, 20),
                line("S6SX:17592222", 20, 60),
                line("PDM023-2007", 20, 100),
            ],
            720,
            1280,
        )
        is None
    )


def test_plain_reading_still_supported():
    assert _ocr_reading_candidate([line("01234", 20, 20)], 720, 1280) is not None


def test_padding_at_image_edge_stays_in_bounds():
    result = _ocr_reading_candidate([line("01234", 0, 0)], 140, 30)
    assert result is not None
    assert result[0] == (0, 0, 140, 30)
