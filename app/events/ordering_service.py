from __future__ import annotations

from collections.abc import Sequence

from app.models.order_event_raw import OrderEventRaw


def sort_events_by_created_at(events: Sequence[OrderEventRaw]) -> list[OrderEventRaw]:
    return sorted(events, key=lambda event: (event.event_created_at, event.ifood_event_id))
