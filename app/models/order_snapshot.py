from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class OrderSnapshot(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_snapshots"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    source_event_id: Mapped[int | None] = mapped_column(ForeignKey("order_events_raw.id"), nullable=True)
    snapshot_type: Mapped[str] = mapped_column(String(20), default="FULL", nullable=False)
    fetch_source: Mapped[str] = mapped_column(String(20), default="EVENT", nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    order = relationship("Order", back_populates="snapshots")
    source_event = relationship("OrderEventRaw", back_populates="snapshots")
