from types import SimpleNamespace

import pytest

from app.actions.action_service import ActionService
from app.actions.base import ActionExecutionResult


class DummyIfoodClient:
    async def confirm_order(self, order_id: str):  # pragma: no cover - should not be called here
        raise AssertionError(f"confirm_order should not be called in this test: {order_id}")


@pytest.mark.asyncio
async def test_maybe_execute_for_event_skips_when_active_mode_disabled() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=False, enabled_automatic_actions={"confirm"}),
    )

    result = await service.maybe_execute_for_event(
        session=None,  # type: ignore[arg-type]
        order=SimpleNamespace(),
        event=SimpleNamespace(),
        action_name="confirm",
    )

    assert result.executed is False
    assert result.skipped is True
    assert result.skip_reason == "ACTIVE_MODE_DISABLED"


@pytest.mark.asyncio
async def test_maybe_execute_for_event_skips_when_action_not_enabled() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=True, enabled_automatic_actions=set()),
    )

    result = await service.maybe_execute_for_event(
        session=None,  # type: ignore[arg-type]
        order=SimpleNamespace(),
        event=SimpleNamespace(),
        action_name="confirm",
    )

    assert result.executed is False
    assert result.skipped is True
    assert result.skip_reason == "AUTO_ACTION_NOT_ENABLED"


@pytest.mark.asyncio
async def test_maybe_execute_for_event_executes_auto_confirm_when_enabled() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=True, enabled_automatic_actions={"confirm"}),
    )

    async def fake_confirm_order(session, order, *, event=None, trigger_mode="MANUAL"):
        return ActionExecutionResult(
            action_type="confirm",
            executed=True,
            success=True,
            skipped=False,
            skip_reason=None,
            action_request_id=1,
            http_status=202,
            response_body=None,
        )

    service.confirm_order = fake_confirm_order  # type: ignore[method-assign]

    result = await service.maybe_execute_for_event(
        session=None,  # type: ignore[arg-type]
        order=SimpleNamespace(current_status="ORDER_STATUS.PLACED", order_timing="IMMEDIATE"),
        event=SimpleNamespace(),
        action_name="confirm",
    )

    assert result.executed is True
    assert result.success is True
    assert result.skipped is False


@pytest.mark.asyncio
async def test_maybe_execute_for_event_skips_auto_confirm_for_scheduled_order() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=True, enabled_automatic_actions={"confirm"}),
    )

    result = await service.maybe_execute_for_event(
        session=None,  # type: ignore[arg-type]
        order=SimpleNamespace(current_status="ORDER_STATUS.PLACED", order_timing="SCHEDULED"),
        event=SimpleNamespace(),
        action_name="confirm",
    )

    assert result.executed is False
    assert result.skipped is True
    assert result.skip_reason == "SCHEDULED_ORDER_REQUIRES_MANUAL_CONFIRMATION"


def test_validate_action_context_blocks_dispatch_for_takeout() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=False, enabled_automatic_actions={"confirm"}),
    )

    result = service._validate_action_context(
        SimpleNamespace(current_status="ORDER_STATUS.READY_TO_PICKUP", order_type="TAKEOUT"),
        "dispatch",
    )

    assert result.allowed is False
    assert result.reason == "ORDER_TYPE_NOT_VALID_FOR_DISPATCH"


def test_validate_action_context_requires_confirmed_for_start_preparation() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=False, enabled_automatic_actions={"confirm"}),
    )

    result = service._validate_action_context(
        SimpleNamespace(current_status="ORDER_STATUS.PLACED", order_type="DELIVERY"),
        "startPreparation",
    )

    assert result.allowed is False
    assert result.reason == "ORDER_STATUS_NOT_VALID_FOR_START_PREPARATION"


def test_validate_action_context_allows_ready_to_pickup_for_takeout_in_preparation() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=False, enabled_automatic_actions={"confirm"}),
    )

    result = service._validate_action_context(
        SimpleNamespace(current_status="ORDER_STATUS.PREPARATION_STARTED", order_type="TAKEOUT"),
        "readyToPickup",
    )

    assert result.allowed is True


def test_validate_action_context_blocks_request_cancellation_after_ready_to_pickup() -> None:
    service = ActionService(
        DummyIfoodClient(),
        SimpleNamespace(orders_active_mode=False, enabled_automatic_actions={"confirm"}),
    )

    result = service._validate_action_context(
        SimpleNamespace(current_status="ORDER_STATUS.READY_TO_PICKUP", order_type="DELIVERY"),
        "requestCancellation",
    )

    assert result.allowed is False
    assert result.reason == "ORDER_STATUS_NOT_VALID_FOR_REQUEST_CANCELLATION"
