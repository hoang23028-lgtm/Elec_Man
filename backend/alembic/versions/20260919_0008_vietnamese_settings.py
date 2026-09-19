"""Vietnamese descriptions for system settings.

Revision ID: 20260919_0008
Revises: 20260918_0007
Create Date: 2026-09-19
"""

import sqlalchemy as sa

from alembic import op

revision = "20260919_0008"
down_revision = "20260918_0007"
branch_labels = None
depends_on = None


VIETNAMESE_DESCRIPTIONS = {
    "confidence_ok_threshold": (
        "Độ tin cậy tối thiểu để mô hình sản xuất đề xuất tự động chấp nhận."
    ),
    "confidence_review_threshold": (
        "Ngưỡng độ tin cậy dùng để ưu tiên kết quả cần kiểm duyệt thủ công."
    ),
    "max_upload_size_mb": (
        "Giới hạn dung lượng tải lên trong vận hành; cấu hình môi trường có hiệu lực "
        "sau khi khởi động lại."
    ),
    "max_retry_count": ("Số lần xử lý lại tối đa áp dụng cho tiến trình xử lý mới triển khai."),
    "data_retention_days": ("Thời gian dự kiến lưu trữ dữ liệu; hệ thống chưa bật xóa tự động."),
    "worker_poll_interval_seconds": (
        "Chu kỳ kiểm tra mong muốn, được áp dụng sau khi khởi động lại tiến trình xử lý."
    ),
}

ENGLISH_DESCRIPTIONS = {
    "confidence_ok_threshold": (
        "Minimum confidence for a future production model to propose auto-pass."
    ),
    "confidence_review_threshold": ("Confidence boundary used to prioritize manual review."),
    "max_upload_size_mb": (
        "Operational upload-size policy. Environment configuration remains the "
        "enforcement source until restart."
    ),
    "max_retry_count": "Desired processing retry limit for newly deployed workers.",
    "data_retention_days": "Retention planning value. No automatic deletion is enabled.",
    "worker_poll_interval_seconds": (
        "Desired worker polling interval applied on deployment restart."
    ),
}


def _update_descriptions(descriptions: dict[str, str]) -> None:
    table = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("description", sa.Text),
    )
    for key, description in descriptions.items():
        op.execute(table.update().where(table.c.key == key).values(description=description))


def upgrade() -> None:
    _update_descriptions(VIETNAMESE_DESCRIPTIONS)


def downgrade() -> None:
    _update_descriptions(ENGLISH_DESCRIPTIONS)
