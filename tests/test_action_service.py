from types import SimpleNamespace

import pytest

from app.actions.action_service import ActionService


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
