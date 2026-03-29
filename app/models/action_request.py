from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class ActionRequest(Base, IdMixin, TimestampMixin):
    __tablename__ = "action_requests"
    __table_args__ = (
        UniqueConstraint("order_id", "action_type", "source_event_id", name="uq_action_requests_order_action_event"),
    )

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    source_event_id: Mapped[int | None] = mapped_column(ForeignKey("order_events_raw.id"), nullable=True)
    confirmed_by_event_id: Mapped[int | None] = mapped_column(ForeignKey("order_events_raw.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    active_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_body: Mapped[dict | list[dict] | None] = mapped_column(JSONB, nullable=True)
    result_status: Mapped[str] = mapped_column(String(30), nullable=False)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    external_confirmation_expected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    order = relationship("Order", back_populates="action_requests")
    merchant = relationship("Merchant", back_populates="action_requests")
    source_event = relationship(
        "OrderEventRaw",
        back_populates="source_action_requests",
        foreign_keys=[source_event_id],
    )
    confirmed_by_event = relationship(
        "OrderEventRaw",
        back_populates="confirmation_action_requests",
        foreign_keys=[confirmed_by_event_id],
    )
    integration_logs = relationship("IntegrationLog", back_populates="action_request")
