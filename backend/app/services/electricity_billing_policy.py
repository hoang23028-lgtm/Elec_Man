"""Verified, append-only electricity price and VAT versions.

Monthly indices cannot split consumption at a mid-month tariff change. Only
months wholly covered by a version are billable; never reuse today's price for
unverified historical periods. These are estimates, not posted tax invoices.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


def as_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def next_month(value: date) -> date:
    return date(value.year + value.month // 12, value.month % 12 + 1, 1)


@dataclass(frozen=True)
class EffectiveVersion:
    code: str
    source_url: str
    effective_from: date
    effective_until: date | None  # Exclusive.

    @property
    def first_full_month(self) -> date:
        start = self.effective_from
        return start if start.day == 1 else next_month(start)

    @property
    def full_months_until(self) -> date | None:
        return self.effective_until.replace(day=1) if self.effective_until else None

    def covers_month(self, value: date | datetime) -> bool:
        month = as_date(value).replace(day=1)
        return self.first_full_month <= month and (
            self.full_months_until is None or month < self.full_months_until
        )


@dataclass(frozen=True)
class TariffVersion(EffectiveVersion):
    residential_prices: tuple[int, ...]
    production_price: int
    commercial_price: int
    school_medical_price: int
    administrative_price: int

    @property
    def residential_tiers(self) -> tuple[tuple[Decimal | None, Decimal], ...]:
        return tuple(
            (Decimal(allowance) if allowance is not None else None, Decimal(price))
            for allowance, price in zip((50, 50, 100, 100, 100, None), self.residential_prices)
        )

    def flat_tariff(self, purpose: str) -> tuple[str, int] | None:
        return {
            "SAN_XUAT": ("Sản xuất dưới 6 kV, giờ bình thường", self.production_price),
            "KINH_DOANH": ("Kinh doanh dưới 6 kV, giờ bình thường", self.commercial_price),
            "TRUONG_HOC_Y_TE": ("Trường học/Y tế dưới 6 kV", self.school_medical_price),
            "UB_HANH_CHINH": ("Hành chính sự nghiệp dưới 6 kV", self.administrative_price),
        }.get(normalize_purpose(purpose))


@dataclass(frozen=True)
class VatVersion(EffectiveVersion):
    rate: Decimal


PURPOSE_ALIASES = {
    "HO_SAN_XUAT": "SAN_XUAT",
    "HO_KINH_DOANH": "KINH_DOANH",
    "VIETTEL": "KINH_DOANH",
}
FLAT_PURPOSES = (
    "SAN_XUAT",
    "HO_SAN_XUAT",
    "KINH_DOANH",
    "HO_KINH_DOANH",
    "VIETTEL",
    "TRUONG_HOC_Y_TE",
    "UB_HANH_CHINH",
)


def normalize_purpose(value: str) -> str:
    purpose = value.strip().upper()
    return PURPOSE_ALIASES.get(purpose, purpose)


# Source table compares both decisions, including every supported purpose:
# https://www.cskh.evnspc.vn/TraCuu/ThongTinGiaDien
TARIFF_VERSIONS = (
    TariffVersion(
        code="2699/QĐ-BCT",
        source_url="https://www.cskh.evnspc.vn/TraCuu/ThongTinGiaDien",
        effective_from=date(2024, 10, 11),
        effective_until=date(2025, 5, 10),
        residential_prices=(1893, 1956, 2271, 2860, 3197, 3302),
        production_price=1896,
        commercial_price=3007,
        school_medical_price=1977,
        administrative_price=2124,
    ),
    TariffVersion(
        code="1279/QĐ-BCT",
        source_url="https://vanban.chinhphu.vn/?classid=2&docid=213617&pageid=27160",
        effective_from=date(2025, 5, 10),
        effective_until=None,
        residential_prices=(1984, 2050, 2380, 2998, 3350, 3460),
        production_price=1987,
        commercial_price=3152,
        school_medical_price=2072,
        administrative_price=2226,
    ),
)

# Older VAT periods deliberately stay unsupported until their sources are verified.
VAT_VERSIONS = (
    VatVersion(
        "180/2024/NĐ-CP",
        "https://vanban.chinhphu.vn/?classid=0&docid=212248&pageid=27160",
        date(2025, 1, 1),
        date(2025, 7, 1),
        Decimal("0.08"),
    ),
    VatVersion(
        "204/2025/QH15",
        "https://vanban.chinhphu.vn/default.aspx?docid=214209&pageid=27160",
        date(2025, 7, 1),
        date(2027, 1, 1),
        Decimal("0.08"),
    ),
    VatVersion(
        "48/2024/QH15 · mức thông thường sau kỳ giảm thuế",
        "https://vanban.chinhphu.vn/?docid=212476&pageid=27160",
        date(2027, 1, 1),
        None,
        Decimal("0.10"),
    ),
)


def tariff_for_month(value: date | datetime) -> TariffVersion | None:
    return next((version for version in TARIFF_VERSIONS if version.covers_month(value)), None)


def vat_for_month(value: date | datetime) -> VatVersion | None:
    return next((version for version in VAT_VERSIONS if version.covers_month(value)), None)


def billing_unavailable_reason(
    consumption: Decimal | None, purpose: str, month: date | datetime
) -> str | None:
    if consumption is None or not consumption.is_finite() or consumption < 0:
        return "Thiếu kỳ liền trước hoặc chỉ số giảm; cần đối soát trước khi tính tiền."
    tariff = tariff_for_month(month)
    if tariff is None:
        start = as_date(month).replace(day=1)
        if any(start < version.effective_from < next_month(start) for version in TARIFF_VERSIONS):
            return "Tháng đổi giá giữa kỳ; chưa có chỉ số/ngày chốt để phân bổ theo hai biểu giá."
        return "Chưa có biểu giá đã xác minh cho kỳ này."
    if vat_for_month(month) is None:
        return "Chưa có chính sách VAT đã xác minh cho kỳ này."
    if normalize_purpose(purpose) != "SINH_HOAT" and tariff.flat_tariff(purpose) is None:
        return "Mục đích sử dụng chưa có biểu giá tương ứng."
    return None
