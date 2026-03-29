from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class IntegrationLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "integration_logs"

    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    order_event_id: Mapped[int | None] = mapped_column(ForeignKey("order_events_raw.id"), nullable=True)
    polling_run_id: Mapped[int | None] = mapped_column(ForeignKey("event_polling_runs.id"), nullable=True)
    action_request_id: Mapped[int | None] = mapped_column(ForeignKey("action_requests.id"), nullable=True)
    integration_name: Mapped[str] = mapped_column(String(50), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    http_method: Mapped[str] = mapped_column(String(10), nullable=False)
    url_path: Mapped[str] = mapped_column(String(255), nullable=False)
    request_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)

    merchant = relationship("Merchant", back_populates="integration_logs")
    order = relationship("Order", back_populates="integration_logs")
    order_event = relationship("OrderEventRaw", back_populates="integration_logs")
    polling_run = relationship("EventPollingRun", back_populates="integration_logs")
    action_request = relationship("ActionRequest", back_populates="integration_logs")
