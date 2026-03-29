from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class OrderStatusHistory(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_status_history"
    __table_args__ = (UniqueConstraint("source_event_id", name="uq_order_status_history_source_event_id"),)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    source_event_id: Mapped[int | None] = mapped_column(ForeignKey("order_events_raw.id"), nullable=True)
    status_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status_full_code: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="EVENT", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order = relationship("Order", back_populates="status_history")
    source_event = relationship("OrderEventRaw", back_populates="status_history_entries")
