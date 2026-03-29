from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.event_processing_state import EventProcessingState
from app.models.order_event_raw import OrderEventRaw


def filter_new_events(events: Sequence[OrderEventRaw]) -> list[OrderEventRaw]:
    return [
        event
        for event in events
        if event.processing_state
        and event.processing_state.processing_status in {"PENDING", "RETRY"}
    ]


def build_processable_events_query(limit: int | None = None) -> Select[tuple[OrderEventRaw]]:
    now = datetime.now(timezone.utc)
    query = (
        select(OrderEventRaw)
        .join(EventProcessingState, EventProcessingState.order_event_id == OrderEventRaw.id)
        .options(selectinload(OrderEventRaw.processing_state))
        .where(
            EventProcessingState.processing_status.in_(["PENDING", "RETRY"]),
            or_(
                EventProcessingState.next_retry_at.is_(None),
                EventProcessingState.next_retry_at <= now,
            ),
        )
        .order_by(OrderEventRaw.event_created_at.asc(), OrderEventRaw.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query


def list_processable_events(session: Session, limit: int | None = None) -> list[OrderEventRaw]:
    return list(session.scalars(build_processable_events_query(limit=limit)))
