from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class OrderItem(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_items"
    __table_args__ = (UniqueConstraint("order_id", "item_sequence", name="uq_order_items_order_sequence"),)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    item_sequence: Mapped[int] = mapped_column(nullable=False)
    ifood_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    unique_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    integration_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    item_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_index: Mapped[int | None] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    unit_price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    options_price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)

    order = relationship("Order", back_populates="items")
    options = relationship("OrderItemOption", back_populates="order_item", cascade="all, delete-orphan")
