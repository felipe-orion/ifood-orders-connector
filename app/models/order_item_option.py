from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class OrderItemOption(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_item_options"
    __table_args__ = (
        UniqueConstraint("order_item_id", "option_sequence", name="uq_order_item_options_item_sequence"),
    )

    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False)
    option_sequence: Mapped[int] = mapped_column(nullable=False)
    ifood_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    unique_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    integration_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    addition: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    unit_price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    customization_json: Mapped[dict | list[dict] | None] = mapped_column(JSONB, nullable=True)

    order_item = relationship("OrderItem", back_populates="options")
