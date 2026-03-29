from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class OrderEventReceipt(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_event_receipts"
    __table_args__ = (
        UniqueConstraint("polling_run_id", "receipt_index", name="uq_order_event_receipts_run_receipt_index"),
    )

    polling_run_id: Mapped[int] = mapped_column(ForeignKey("event_polling_runs.id"), nullable=False)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    receipt_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ifood_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ifood_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_code: Mapped[str] = mapped_column(String(10), nullable=False)
    event_full_code: Mapped[str] = mapped_column(String(100), nullable=False)
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sales_channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    polling_run = relationship("EventPollingRun", back_populates="receipts")
    merchant = relationship("Merchant", back_populates="event_receipts")
