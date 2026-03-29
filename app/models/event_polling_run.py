from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class EventPollingRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "event_polling_runs"
    __table_args__ = (UniqueConstraint("run_uuid", name="uq_event_polling_runs_run_uuid"),)

    run_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ack_attempted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ack_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)

    receipts = relationship("OrderEventReceipt", back_populates="polling_run")
    ack_batches = relationship("OrderEventAcknowledgmentBatch", back_populates="polling_run")
    integration_logs = relationship("IntegrationLog", back_populates="polling_run")
