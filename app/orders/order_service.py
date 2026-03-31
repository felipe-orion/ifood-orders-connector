from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.events.event_classifier import extract_event_key
from app.models.event_processing_state import EventProcessingState
from app.models.order import Order
from app.models.order_event_raw import OrderEventRaw
from app.models.order_status_history import OrderStatusHistory
from app.orders.fetcher import OrderFetcher
from app.orders.normalizer import normalize_order
from app.orders.persister import OrderPersister
from app.orders.retry_policy import RetryableOrderFetchError, next_retry_at

logger = get_logger(__name__)


class OrderService:
    def __init__(
        self,
        fetcher: OrderFetcher,
        *,
        normalizer=normalize_order,
        persister_cls=OrderPersister,
    ) -> None:
        self.fetcher = fetcher
        self.normalizer = normalizer
        self.persister_cls = persister_cls

    async def ingest_order_from_event(self, session: Session, event: OrderEventRaw) -> Order:
        state = event.processing_state

        try:
            raw_order = await self.fetcher.fetch_order_details(event)
            normalized_order = self.normalizer(raw_order)
            order = self.persister_cls(session).save_order_snapshot(
                merchant_id=event.merchant_id,
                source_event=event,
                normalized_order=normalized_order,
                raw_payload=raw_order,
            )
            if order.placed_at is None:
                order.placed_at = event.event_created_at
            self._append_status_history(session, order, event)
            self._mark_processed(state)
            logger.info(
                "Order fetched and normalized.",
                extra={
                    "ifood_order_id": str(event.ifood_order_id),
                    "ifood_event_id": str(event.ifood_event_id),
                    "current_status": order.current_status,
                    "items_count": len(order.items),
                    "payments_count": len(order.payments),
                    "benefits_count": len(order.benefits),
                },
            )
            return order
        except RetryableOrderFetchError as exc:
            self._mark_retry(state, str(exc))
            raise
        except Exception as exc:
            self._mark_failed(state, str(exc))
            raise

    async def apply_status_event(
        self,
        session: Session,
        event: OrderEventRaw,
        *,
        append_history: bool = True,
    ) -> Order | None:
        order = session.scalar(select(Order).where(Order.ifood_order_id == event.ifood_order_id))
        if not order:
            if event.processing_state:
                self._mark_retry(
                    event.processing_state,
                    "Order not found locally yet for status event.",
                    error_code="ORDER_NOT_FOUND_LOCALLY",
                )
            logger.warning(
                "Status event will be retried because order is not persisted yet.",
                extra={
                    "ifood_order_id": str(event.ifood_order_id),
                    "ifood_event_id": str(event.ifood_event_id),
                    "event_full_code": event.event_full_code,
                },
            )
            return None

        order.current_status = event.event_full_code
        order.latest_event_created_at = event.event_created_at
        event_key = extract_event_key(event.event_code, event.event_full_code)

        if event_key == "CONFIRMED":
            order.confirmed_at = event.event_created_at
        elif event_key in {"PREPARATION_STARTED", "IN_PREPARATION", "PREPARING"}:
            order.preparation_start_at = event.event_created_at
        elif event_key == "READY_TO_PICKUP":
            order.ready_to_pickup_at = event.event_created_at
        elif event_key == "DISPATCHED":
            order.dispatched_at = event.event_created_at
        elif event_key == "CONCLUDED":
            order.concluded_at = event.event_created_at
        elif event_key == "CANCELLED":
            order.cancelled_at = event.event_created_at

        if append_history:
            self._append_status_history(session, order, event)
        if event.processing_state:
            self._mark_processed(event.processing_state)
        logger.info(
            "Order status updated from event.",
            extra={
                "ifood_order_id": str(event.ifood_order_id),
                "ifood_event_id": str(event.ifood_event_id),
                "current_status": order.current_status,
                "append_history": append_history,
            },
        )
        return order

    def _append_status_history(self, session: Session, order: Order, event: OrderEventRaw) -> None:
        existing = session.scalar(
            select(OrderStatusHistory).where(OrderStatusHistory.source_event_id == event.id)
        )
        if existing:
            return

        history = OrderStatusHistory(
            order_id=order.id,
            source_event_id=event.id,
            status_code=event.event_code,
            status_full_code=event.event_full_code,
            occurred_at=event.event_created_at,
            source="EVENT",
        )
        session.add(history)

    @staticmethod
    def _mark_processed(state: EventProcessingState | None) -> None:
        if not state:
            return
        state.processing_status = "PROCESSED"
        state.processed_at = datetime.now(timezone.utc)
        state.last_error_code = None
        state.last_error_message = None
        state.next_retry_at = None

    @staticmethod
    def _mark_retry(
        state: EventProcessingState | None,
        message: str,
        *,
        error_code: str = "ORDER_NOT_AVAILABLE",
    ) -> None:
        if not state:
            return
        state.processing_status = "RETRY"
        state.last_error_code = error_code
        state.last_error_message = message
        state.next_retry_at = next_retry_at(state.attempt_count)

    @staticmethod
    def _mark_failed(state: EventProcessingState | None, message: str) -> None:
        if not state:
            return
        state.processing_status = "FAILED"
        state.last_error_code = "UNEXPECTED_ERROR"
        state.last_error_message = message
