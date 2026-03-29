from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class OrderCustomer(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_customers"
    __table_args__ = (UniqueConstraint("order_id", name="uq_order_customers_order_id"),)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    ifood_customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone_localizer: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_localizer_expiration: Mapped[str | None] = mapped_column(String(50), nullable=True)
    orders_count_on_merchant: Mapped[int | None] = mapped_column(nullable=True)
    segmentation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    order = relationship("Order", back_populates="customer")
