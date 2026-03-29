from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.event_classifier import classify_event, normalize_event_code, normalize_event_full_code
from app.models.event_polling_run import EventPollingRun
from app.models.event_processing_state import EventProcessingState
from app.models.merchant import Merchant
from app.models.order_event_raw import OrderEventRaw
from app.models.order_event_receipt import OrderEventReceipt


@dataclass
class PersistenceResult:
    canonical_events: list[OrderEventRaw]
    new_event_count: int
    duplicate_event_count: int


def create_polling_run(session: Session) -> EventPollingRun:
    polling_run = EventPollingRun()
    session.add(polling_run)
    session.flush()
    return polling_run


def _get_or_create_merchant(session: Session, ifood_merchant_id: uuid.UUID) -> Merchant:
    merchant = session.scalar(
        select(Merchant).where(Merchant.ifood_merchant_id == ifood_merchant_id)
    )
    if merchant:
        merchant.last_seen_at = datetime.now(timezone.utc)
        return merchant

    merchant = Merchant(ifood_merchant_id=ifood_merchant_id)
    session.add(merchant)
    session.flush()
    return merchant


def store_polled_events(
    session: Session,
    polling_run: EventPollingRun,
    events_payload: list[dict],
) -> PersistenceResult:
    canonical_events: list[OrderEventRaw] = []
    new_event_count = 0
    duplicate_event_count = 0

    for index, payload in enumerate(events_payload):
        received_at = datetime.now(timezone.utc)
        merchant = _get_or_create_merchant(session, uuid.UUID(str(payload["merchantId"])))

        receipt = OrderEventReceipt(
            polling_run_id=polling_run.id,
            merchant_id=merchant.id,
            receipt_index=index,
            ifood_event_id=uuid.UUID(str(payload["id"])),
            ifood_order_id=uuid.UUID(str(payload["orderId"])),
            event_code=normalize_event_code(payload["code"]),
            event_full_code=normalize_event_full_code(payload["fullCode"]),
            event_created_at=datetime.fromisoformat(payload["createdAt"].replace("Z", "+00:00")),
            sales_channel=payload.get("salesChannel"),
            event_metadata=payload.get("metadata"),
            raw_payload=payload,
            received_at=received_at,
        )
        session.add(receipt)

        existing_event = session.scalar(
            select(OrderEventRaw).where(OrderEventRaw.ifood_event_id == receipt.ifood_event_id)
        )

        if existing_event:
            existing_event.last_received_at = received_at
            existing_event.receive_count += 1
            duplicate_event_count += 1
            canonical_events.append(existing_event)
            continue

        raw_event = OrderEventRaw(
            merchant_id=merchant.id,
            ifood_event_id=receipt.ifood_event_id,
            ifood_order_id=receipt.ifood_order_id,
            event_code=receipt.event_code,
            event_full_code=receipt.event_full_code,
            event_created_at=receipt.event_created_at,
            sales_channel=receipt.sales_channel,
            event_metadata=receipt.event_metadata,
            raw_payload=payload,
            first_received_at=received_at,
            last_received_at=received_at,
            receive_count=1,
            first_polling_run_id=polling_run.id,
        )
        session.add(raw_event)
        session.flush()

        classification = classify_event(raw_event.event_code, raw_event.event_full_code)
        processing_state = EventProcessingState(
            order_event_id=raw_event.id,
            processing_status="PENDING",
            classified_as=classification.classification,
            requires_order_fetch=classification.requires_order_fetch,
        )
        session.add(processing_state)

        canonical_events.append(raw_event)
        new_event_count += 1

    polling_run.response_event_count = len(events_payload)
    polling_run.new_event_count = new_event_count
    polling_run.duplicate_event_count = duplicate_event_count
    session.flush()

    return PersistenceResult(
        canonical_events=canonical_events,
        new_event_count=new_event_count,
        duplicate_event_count=duplicate_event_count,
    )
