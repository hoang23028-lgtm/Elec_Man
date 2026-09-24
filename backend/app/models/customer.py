from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_lookup_key", "lookup_key", unique=True),
        Index("ix_customers_route", "electricity_route"),
    )

    customer_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    lookup_key: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    electricity_route: Mapped[str] = mapped_column(String(255), nullable=False)
    meter_serial: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    initial_reading: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_purpose: Mapped[str] = mapped_column(String(64), nullable=False)
