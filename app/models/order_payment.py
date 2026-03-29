from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class OrderPayment(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_payments"
    __table_args__ = (UniqueConstraint("order_id", "payment_sequence", name="uq_order_payments_order_sequence"),)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    payment_sequence: Mapped[int] = mapped_column(nullable=False)
    method: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prepaid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    change_for_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    card_brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    authorization_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acquirer_document: Mapped[str | None] = mapped_column(String(100), nullable=True)

    order = relationship("Order", back_populates="payments")
