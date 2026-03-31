from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.actions.action_service import ActionService
from app.events.event_classifier import classify_event
from app.models.order_event_raw import OrderEventRaw
from app.orders.order_service import OrderService


@dataclass(frozen=True)
class EventProcessingResult:
    event_id: str
    order_id: str
    classification: str
    processing_status: str
    requires_order_fetch: bool
    updates_status: bool
    suggested_action: str | None
    action_executed: bool = False
    action_success: bool | None = None
    action_skipped: bool = False
    action_skip_reason: str | None = None


class EventProcessor:
    def __init__(self, order_service: OrderService, action_service: ActionService) -> None:
        self.order_service = order_service
        self.action_service = action_service

    async def process_event(self, session: Session, event: OrderEventRaw) -> EventProcessingResult:
        classification = classify_event(event.event_code, event.event_full_code)
        self._mark_processing_started(event)

        if classification.requires_order_fetch:
            order = await self.order_service.ingest_order_from_event(session, event)
            if classification.updates_status:
                order = await self.order_service.apply_status_event(
                    session,
                    event,
                    append_history=False,
                ) or order
            action_result = await self.action_service.maybe_execute_for_event(
                session,
                order=order,
                event=event,
                action_name=classification.auto_action,
            )
            return EventProcessingResult(
                event_id=str(event.ifood_event_id),
                order_id=str(event.ifood_order_id),
                classification=classification.classification,
                processing_status=event.processing_state.processing_status if event.processing_state else "PROCESSED",
                requires_order_fetch=classification.requires_order_fetch,
                updates_status=classification.updates_status,
                suggested_action=classification.auto_action,
                action_executed=action_result.executed,
                action_success=action_result.success,
                action_skipped=action_result.skipped,
                action_skip_reason=action_result.skip_reason,
            )

        if classification.updates_status:
            await self.order_service.apply_status_event(session, event)
            return EventProcessingResult(
                event_id=str(event.ifood_event_id),
                order_id=str(event.ifood_order_id),
                classification=classification.classification,
                processing_status=event.processing_state.processing_status if event.processing_state else "PROCESSED",
                requires_order_fetch=classification.requires_order_fetch,
                updates_status=classification.updates_status,
                suggested_action=classification.auto_action,
            )

        if event.processing_state:
            event.processing_state.processing_status = "IGNORED"
            event.processing_state.processed_at = datetime.now(timezone.utc)
            event.processing_state.last_error_code = None
            event.processing_state.last_error_message = None
            event.processing_state.next_retry_at = None
        return EventProcessingResult(
            event_id=str(event.ifood_event_id),
            order_id=str(event.ifood_order_id),
            classification=classification.classification,
            processing_status=event.processing_state.processing_status if event.processing_state else "IGNORED",
            requires_order_fetch=classification.requires_order_fetch,
            updates_status=classification.updates_status,
            suggested_action=classification.auto_action,
        )

    @staticmethod
    def _mark_processing_started(event: OrderEventRaw) -> None:
        if not event.processing_state:
            return
        event.processing_state.processing_status = "PROCESSING"
        event.processing_state.attempt_count += 1
        event.processing_state.last_attempt_at = datetime.now(timezone.utc)
