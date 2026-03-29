from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class Merchant(Base, IdMixin, TimestampMixin):
    __tablename__ = "merchants"
    __table_args__ = (UniqueConstraint("ifood_merchant_id", name="uq_merchants_ifood_merchant_id"),)

    ifood_merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    event_receipts = relationship("OrderEventReceipt", back_populates="merchant")
    raw_events = relationship("OrderEventRaw", back_populates="merchant")
    orders = relationship("Order", back_populates="merchant")
    action_requests = relationship("ActionRequest", back_populates="merchant")
    integration_logs = relationship("IntegrationLog", back_populates="merchant")
