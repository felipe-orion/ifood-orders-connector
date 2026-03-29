from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class OrderEventAcknowledgmentBatch(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_event_acknowledgment_batches"

    polling_run_id: Mapped[int] = mapped_column(ForeignKey("event_polling_runs.id"), nullable=False)
    requested_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    acknowledged_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    request_payload: Mapped[dict | list[dict]] = mapped_column(JSONB, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)

    polling_run = relationship("EventPollingRun", back_populates="ack_batches")
    items = relationship(
        "OrderEventAcknowledgmentItem",
        back_populates="ack_batch",
        cascade="all, delete-orphan",
    )


class OrderEventAcknowledgmentItem(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_event_acknowledgment_items"
    __table_args__ = (
        UniqueConstraint("ack_batch_id", "ifood_event_id", name="uq_order_event_ack_items_batch_event"),
    )

    ack_batch_id: Mapped[int] = mapped_column(ForeignKey("order_event_acknowledgment_batches.id"), nullable=False)
    order_event_id: Mapped[int | None] = mapped_column(ForeignKey("order_events_raw.id"), nullable=True)
    ifood_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    item_result_status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ack_batch = relationship("OrderEventAcknowledgmentBatch", back_populates="items")
    order_event = relationship("OrderEventRaw", back_populates="ack_items")
