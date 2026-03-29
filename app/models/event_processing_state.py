from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class EventProcessingState(Base, IdMixin, TimestampMixin):
    __tablename__ = "event_processing_state"
    __table_args__ = (UniqueConstraint("order_event_id", name="uq_event_processing_state_order_event_id"),)

    order_event_id: Mapped[int] = mapped_column(ForeignKey("order_events_raw.id"), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    classified_as: Mapped[str] = mapped_column(String(50), nullable=False)
    requires_order_fetch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)

    order_event = relationship("OrderEventRaw", back_populates="processing_state")
