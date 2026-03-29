from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class OrderDelivery(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_deliveries"
    __table_args__ = (UniqueConstraint("order_id", name="uq_order_deliveries_order_id"),)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    delivery_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    delivered_by: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_complement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_neighborhood: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    pickup_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    takeout_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schedule_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schedule_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="delivery")
