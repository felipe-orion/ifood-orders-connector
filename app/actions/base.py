from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.action_request import ActionRequest
from app.models.order import Order
from app.models.order_event_raw import OrderEventRaw


@dataclass(frozen=True)
class ActionExecutionResult:
    action_type: str
    executed: bool
    success: bool | None
    skipped: bool
    skip_reason: str | None
    action_request_id: int | None
    http_status: int | None
    response_body: dict | list[dict] | None


def create_action_request(
    session: Session,
    *,
    order: Order,
    action_type: str,
    trigger_mode: str,
    active_mode: bool,
    source_event: OrderEventRaw | None,
    request_payload: dict | None,
    external_confirmation_expected: bool = True,
) -> ActionRequest:
    action_request = ActionRequest(
        order_id=order.id,
        merchant_id=order.merchant_id,
        source_event_id=source_event.id if source_event else None,
        action_type=action_type,
        trigger_mode=trigger_mode,
        active_mode=active_mode,
        request_payload=request_payload,
        request_sent_at=datetime.now(timezone.utc),
        result_status="PENDING",
        success=None,
        external_confirmation_expected=external_confirmation_expected,
    )
    session.add(action_request)
    session.flush()
    return action_request


def finalize_action_request(
    action_request: ActionRequest,
    *,
    http_status: int | None,
    response_body: dict | list[dict] | None,
    result_status: str,
    success: bool | None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    action_request.http_status = http_status
    action_request.response_received_at = datetime.now(timezone.utc)
    action_request.response_body = response_body
    action_request.result_status = result_status
    action_request.success = success
    action_request.error_code = error_code
    action_request.error_message = error_message
