from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.order_benefit import OrderBenefit
from app.models.order_customer import OrderCustomer
from app.models.order_delivery import OrderDelivery
from app.models.order_event_raw import OrderEventRaw
from app.models.order_item import OrderItem
from app.models.order_item_option import OrderItemOption
from app.models.order_payment import OrderPayment
from app.models.order_snapshot import OrderSnapshot


class OrderPersister:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_order_snapshot(
        self,
        merchant_id: int,
        source_event: OrderEventRaw,
        normalized_order: dict,
        raw_payload: dict,
    ) -> Order:
        if not normalized_order["header"].get("ifood_order_id"):
            raise ValueError("Normalized order is missing ifood_order_id.")

        order = self.session.scalar(
            select(Order).where(Order.ifood_order_id == uuid.UUID(str(normalized_order["header"]["ifood_order_id"])))
        )
        if not order:
            order = Order(
                merchant_id=merchant_id,
                ifood_order_id=uuid.UUID(str(normalized_order["header"]["ifood_order_id"])),
                first_seen_at=source_event.event_created_at,
            )
            self.session.add(order)
            self.session.flush()

        header = normalized_order["header"]
        external_created_at = _parse_datetime(header.get("external_created_at"))
        preparation_start_at = _parse_datetime(header.get("preparation_start_at"))
        order.sales_channel = header.get("sales_channel")
        order.display_id = header.get("display_id")
        order.category = header.get("category")
        order.order_type = header.get("order_type")
        order.order_timing = header.get("order_timing")
        order.current_status = header.get("current_status") or order.current_status
        order.external_created_at = external_created_at
        order.preparation_start_at = preparation_start_at
        order.currency = header.get("currency") or "BRL"
        order.subtotal_amount = header.get("subtotal_amount")
        order.delivery_fee_amount = header.get("delivery_fee_amount")
        order.benefits_amount = header.get("benefits_amount")
        order.additional_fees_amount = header.get("additional_fees_amount")
        order.total_amount = header.get("total_amount")
        order.payments_pending = header.get("payments_pending")
        order.payments_prepaid = header.get("payments_prepaid")
        order.customer_notes = header.get("customer_notes")
        order.cancellation_source = header.get("cancellation_source")
        order.latest_event_created_at = source_event.event_created_at
        order.last_synced_at = datetime.now(timezone.utc)
        if order.placed_at is None:
            order.placed_at = external_created_at or source_event.event_created_at

        order.customer = self._build_customer(normalized_order["customer"])
        order.delivery = self._build_delivery(normalized_order["delivery"])
        order.items = self._build_items(normalized_order["items"])
        order.payments = [OrderPayment(**payment) for payment in normalized_order["payments"]]
        order.benefits = [OrderBenefit(**benefit) for benefit in normalized_order["benefits"]]

        payload_hash = hashlib.sha256(json.dumps(raw_payload, sort_keys=True).encode("utf-8")).hexdigest()
        existing_snapshot = self.session.scalar(
            select(OrderSnapshot).where(
                OrderSnapshot.order_id == order.id,
                OrderSnapshot.source_event_id == source_event.id,
                OrderSnapshot.payload_hash == payload_hash,
            )
        )

        if not existing_snapshot:
            snapshot = OrderSnapshot(
                order_id=order.id,
                source_event_id=source_event.id,
                snapshot_type="FULL",
                fetch_source="EVENT",
                http_status=200,
                payload_hash=payload_hash,
                raw_payload=raw_payload,
                fetched_at=datetime.now(timezone.utc),
            )
            self.session.add(snapshot)

        self.session.flush()
        return order

    @staticmethod
    def _build_customer(customer_payload: dict | None) -> OrderCustomer | None:
        if not customer_payload:
            return None
        return OrderCustomer(**customer_payload)

    @staticmethod
    def _build_delivery(delivery_payload: dict | None) -> OrderDelivery | None:
        if not delivery_payload:
            return None

        return OrderDelivery(
            **{
                **delivery_payload,
                "delivery_datetime": _parse_datetime(delivery_payload.get("delivery_datetime")),
                "takeout_datetime": _parse_datetime(delivery_payload.get("takeout_datetime")),
                "schedule_start_at": _parse_datetime(delivery_payload.get("schedule_start_at")),
                "schedule_end_at": _parse_datetime(delivery_payload.get("schedule_end_at")),
            }
        )

    @staticmethod
    def _build_items(items_payload: list[dict]) -> list[OrderItem]:
        return [
            OrderItem(
                **{key: value for key, value in item.items() if key != "options"},
                options=[OrderItemOption(**option) for option in item.get("options", [])],
            )
            for item in items_payload
        ]


def _parse_datetime(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
