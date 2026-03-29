from __future__ import annotations

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class OrderBenefit(Base, IdMixin, TimestampMixin):
    __tablename__ = "order_benefits"
    __table_args__ = (UniqueConstraint("order_id", "benefit_sequence", name="uq_order_benefits_order_sequence"),)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    benefit_sequence: Mapped[int] = mapped_column(nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    benefit_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    campaign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sponsorship_values_json: Mapped[dict | list[dict] | None] = mapped_column(JSONB, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="benefits")
