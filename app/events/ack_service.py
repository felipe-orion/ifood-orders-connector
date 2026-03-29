from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.ifood_client import IfoodClient
from app.models.event_polling_run import EventPollingRun
from app.models.order_event_acknowledgment import (
    OrderEventAcknowledgmentBatch,
    OrderEventAcknowledgmentItem,
)
from app.models.order_event_raw import OrderEventRaw


@dataclass
class AckResult:
    success: bool
    status_code: int | None
    acknowledged_event_count: int


async def acknowledge_events(
    session: Session,
    ifood_client: IfoodClient,
    polling_run: EventPollingRun,
    events_payload: list[dict],
) -> AckResult:
    event_ids = [str(event["id"]) for event in events_payload]
    batch = OrderEventAcknowledgmentBatch(
        polling_run_id=polling_run.id,
        requested_event_count=len(event_ids),
        acknowledged_event_count=0,
        request_payload={"events": [{"id": event_id} for event_id in event_ids]},
    )
    session.add(batch)
    session.flush()

    if not event_ids:
        batch.success = True
        batch.response_received_at = datetime.now(timezone.utc)
        polling_run.ack_attempted = False
        polling_run.ack_success = True
        return AckResult(success=True, status_code=None, acknowledged_event_count=0)

    canonical_events = {
        str(event.ifood_event_id): event
        for event in session.scalars(
            select(OrderEventRaw).where(
                OrderEventRaw.ifood_event_id.in_([uuid.UUID(event_id) for event_id in event_ids])
            )
        )
    }

    try:
        response = await ifood_client.ack_events(event_ids)
        response.raise_for_status()
        batch.http_status = response.status_code
        batch.success = True
        batch.acknowledged_event_count = len(event_ids)
        batch.response_received_at = datetime.now(timezone.utc)
        polling_run.ack_attempted = True
        polling_run.ack_success = True

        for event_id in event_ids:
            order_event = canonical_events.get(event_id)
            item = OrderEventAcknowledgmentItem(
                ack_batch_id=batch.id,
                order_event_id=order_event.id if order_event else None,
                ifood_event_id=uuid.UUID(event_id),
                item_result_status="ACKED",
                acked_at=datetime.now(timezone.utc),
            )
            session.add(item)

        return AckResult(success=True, status_code=response.status_code, acknowledged_event_count=len(event_ids))
    except Exception as exc:
        status_code = None
        if hasattr(exc, "response") and getattr(exc, "response") is not None:
            status_code = exc.response.status_code
        batch.success = False
        batch.http_status = status_code
        batch.error_message = str(exc)
        batch.response_received_at = datetime.now(timezone.utc)
        polling_run.ack_attempted = True
        polling_run.ack_success = False
        polling_run.error_message = str(exc)
        for event_id in event_ids:
            order_event = canonical_events.get(event_id)
            item = OrderEventAcknowledgmentItem(
                ack_batch_id=batch.id,
                order_event_id=order_event.id if order_event else None,
                ifood_event_id=uuid.UUID(event_id),
                item_result_status="FAILED",
                acked_at=None,
            )
            session.add(item)
        return AckResult(success=False, status_code=batch.http_status, acknowledged_event_count=0)
