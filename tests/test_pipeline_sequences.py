from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.actions.base import ActionExecutionResult
from app.events.event_processor import EventProcessor


def _processing_state():
    return SimpleNamespace(
        processing_status="PENDING",
        attempt_count=0,
        last_attempt_at=None,
        processed_at=None,
        next_retry_at=None,
        last_error_code=None,
        last_error_message=None,
    )


def _event(event_code: str, event_full_code: str):
    return SimpleNamespace(
        ifood_event_id=uuid4(),
        ifood_order_id=uuid4(),
        event_code=event_code,
        event_full_code=event_full_code,
        processing_state=_processing_state(),
    )


class SequenceOrderService:
    def __init__(self, order):
        self.order = order
        self.fetch_count = 0
        self.status_sequence: list[str] = []

    async def ingest_order_from_event(self, session, event):
        self.fetch_count += 1
        self.order.current_status = event.event_full_code
        event.processing_state.processing_status = "PROCESSED"
        self.status_sequence.append(event.event_full_code)
        return self.order

    async def apply_status_event(self, session, event, *, append_history=True):
        self.order.current_status = event.event_full_code
        event.processing_state.processing_status = "PROCESSED"
        self.status_sequence.append(
            f"{event.event_full_code}|history={append_history}"
        )
        return self.order


class SequenceActionService:
    def __init__(self):
        self.actions: list[str | None] = []

    async def maybe_execute_for_event(self, session, *, order, event, action_name):
        self.actions.append(action_name)
        return ActionExecutionResult(
            action_type=action_name or "none",
            executed=action_name is not None,
            success=True if action_name else None,
            skipped=action_name is None,
            skip_reason=None if action_name else "NO_ACTION_DEFINED",
            action_request_id=1 if action_name else None,
            http_status=202 if action_name else None,
            response_body=None,
        )


@pytest.mark.asyncio
async def test_delivery_immediate_sequence_updates_pipeline() -> None:
    order = SimpleNamespace(
        current_status="UNKNOWN",
        order_type="DELIVERY",
        order_timing="IMMEDIATE",
    )
    order_service = SequenceOrderService(order)
    action_service = SequenceActionService()
    processor = EventProcessor(order_service, action_service)

    sequence = [
        _event("PLC", "ORDER_STATUS.PLACED"),
        _event("CFM", "ORDER_STATUS.CONFIRMED"),
        _event("PRE", "ORDER_STATUS.PREPARATION_STARTED"),
        _event("RTP", "ORDER_STATUS.READY_TO_PICKUP"),
        _event("DSP", "ORDER_STATUS.DISPATCHED"),
    ]

    for event in sequence:
        await processor.process_event(None, event)

    assert order_service.fetch_count == 1
    assert order.current_status == "ORDER_STATUS.DISPATCHED"
    assert action_service.actions == ["confirm"]
    assert order_service.status_sequence == [
        "ORDER_STATUS.PLACED",
        "ORDER_STATUS.PLACED|history=False",
        "ORDER_STATUS.CONFIRMED|history=True",
        "ORDER_STATUS.PREPARATION_STARTED|history=True",
        "ORDER_STATUS.READY_TO_PICKUP|history=True",
        "ORDER_STATUS.DISPATCHED|history=True",
    ]


@pytest.mark.asyncio
async def test_takeout_sequence_finishes_ready_without_dispatch() -> None:
    order = SimpleNamespace(
        current_status="UNKNOWN",
        order_type="TAKEOUT",
        order_timing="IMMEDIATE",
    )
    order_service = SequenceOrderService(order)
    action_service = SequenceActionService()
    processor = EventProcessor(order_service, action_service)

    sequence = [
        _event("PLC", "ORDER_STATUS.PLACED"),
        _event("CFM", "ORDER_STATUS.CONFIRMED"),
        _event("PRE", "ORDER_STATUS.PREPARATION_STARTED"),
        _event("RTP", "ORDER_STATUS.READY_TO_PICKUP"),
    ]

    for event in sequence:
        await processor.process_event(None, event)

    assert order_service.fetch_count == 1
    assert order.current_status == "ORDER_STATUS.READY_TO_PICKUP"
    assert action_service.actions == ["confirm"]
    assert "ORDER_STATUS.DISPATCHED" not in order_service.status_sequence
