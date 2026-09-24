from pydantic import BaseModel, ConfigDict, Field


class CustomerImportRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    customer_code: str = Field(alias="ma_khach_hang", min_length=1, max_length=128)
    full_name: str = Field(alias="ho_ten", min_length=1, max_length=255)
    address: str = Field(alias="dia_chi", min_length=1, max_length=500)
    electricity_route: str = Field(alias="tuyen_dien", min_length=1, max_length=255)
    meter_serial: str = Field(alias="so_seri_cong_to", min_length=1, max_length=128)
    initial_reading: int = Field(alias="chi_so_khoi_tao", ge=0, le=999_999_999)
    usage_purpose: str = Field(alias="muc_dich_su_dung", min_length=1, max_length=64)


class CustomerImportResponse(BaseModel):
    total: int
    created: int
    updated: int
    reconciled_readings: int


class CustomerSummary(BaseModel):
    total: int
    matched_readings: int
    unmatched_readings: int
