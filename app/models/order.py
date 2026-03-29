from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class Order(Base, IdMixin, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("ifood_order_id", name="uq_orders_ifood_order_id"),)

    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    ifood_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    display_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sales_channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    order_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    order_timing: Mapped[str | None] = mapped_column(String(30), nullable=True)
    current_status: Mapped[str] = mapped_column(String(100), default="UNKNOWN", nullable=False)
    external_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preparation_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_to_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    subtotal_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    delivery_fee_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    benefits_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    additional_fees_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    payments_pending: Mapped[bool | None] = mapped_column(nullable=True)
    payments_prepaid: Mapped[bool | None] = mapped_column(nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_event_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    merchant = relationship("Merchant", back_populates="orders")
    snapshots = relationship("OrderSnapshot", back_populates="order", cascade="all, delete-orphan")
    customer = relationship("OrderCustomer", back_populates="order", uselist=False, cascade="all, delete-orphan")
    delivery = relationship("OrderDelivery", back_populates="order", uselist=False, cascade="all, delete-orphan")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan")
    benefits = relationship("OrderBenefit", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")
    action_requests = relationship("ActionRequest", back_populates="order", cascade="all, delete-orphan")
    integration_logs = relationship("IntegrationLog", back_populates="order", cascade="all, delete-orphan")
