from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class OrderEventRaw(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_events_raw"
    __table_args__ = (UniqueConstraint("ifood_event_id", name="uq_order_events_raw_ifood_event_id"),)

    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    ifood_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ifood_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_code: Mapped[str] = mapped_column(String(10), nullable=False)
    event_full_code: Mapped[str] = mapped_column(String(100), nullable=False)
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sales_channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    first_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    receive_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_polling_run_id: Mapped[int] = mapped_column(ForeignKey("event_polling_runs.id"), nullable=False)

    merchant = relationship("Merchant", back_populates="raw_events")
    first_polling_run = relationship("EventPollingRun")
    processing_state = relationship(
        "EventProcessingState",
        back_populates="order_event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ack_items = relationship("OrderEventAcknowledgmentItem", back_populates="order_event")
    status_history_entries = relationship("OrderStatusHistory", back_populates="source_event")
    snapshots = relationship("OrderSnapshot", back_populates="source_event")
    source_action_requests = relationship(
        "ActionRequest",
        back_populates="source_event",
        foreign_keys="ActionRequest.source_event_id",
    )
    confirmation_action_requests = relationship(
        "ActionRequest",
        back_populates="confirmed_by_event",
        foreign_keys="ActionRequest.confirmed_by_event_id",
    )
    integration_logs = relationship("IntegrationLog", back_populates="order_event")
