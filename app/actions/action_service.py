from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.actions.base import ActionExecutionResult, create_action_request, finalize_action_request
from app.actions.cancellation_reasons import CancellationReasonsAction
from app.actions.confirm import ConfirmAction
from app.actions.dispatch import DispatchAction
from app.actions.ready_to_pickup import ReadyToPickupAction
from app.actions.request_cancellation import RequestCancellationAction
from app.actions.start_preparation import StartPreparationAction
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.events.event_classifier import extract_event_key
from app.integrations.ifood_client import IfoodClient, get_ifood_client
from app.models.action_request import ActionRequest
from app.models.order import Order
from app.models.order_event_raw import OrderEventRaw

logger = get_logger(__name__)


@dataclass(frozen=True)
class ActionContextValidation:
    allowed: bool
    reason: str | None = None


class ActionService:
    def __init__(self, ifood_client: IfoodClient, settings: Settings) -> None:
        self.settings = settings
        self.confirm_action = ConfirmAction(ifood_client)
        self.start_preparation_action = StartPreparationAction(ifood_client)
        self.ready_to_pickup_action = ReadyToPickupAction(ifood_client)
        self.dispatch_action = DispatchAction(ifood_client)
        self.cancellation_reasons_action = CancellationReasonsAction(ifood_client)
        self.request_cancellation_action = RequestCancellationAction(ifood_client)

    async def maybe_execute_for_event(
        self,
        session: Session,
        *,
        order: Order,
        event: OrderEventRaw,
        action_name: str | None,
    ) -> ActionExecutionResult:
        if not self.settings.orders_active_mode or not action_name:
            return ActionExecutionResult(
                action_type=action_name or "none",
                executed=False,
                success=None,
                skipped=True,
                skip_reason="ACTIVE_MODE_DISABLED" if not self.settings.orders_active_mode else "NO_ACTION_DEFINED",
                action_request_id=None,
                http_status=None,
                response_body=None,
            )

        if action_name.lower() not in self.settings.enabled_automatic_actions:
            return ActionExecutionResult(
                action_type=action_name,
                executed=False,
                success=None,
                skipped=True,
                skip_reason="AUTO_ACTION_NOT_ENABLED",
                action_request_id=None,
                http_status=None,
                response_body=None,
            )

        automation_validation = self._validate_automatic_action_context(order, action_name)
        if not automation_validation.allowed:
            return ActionExecutionResult(
                action_type=action_name,
                executed=False,
                success=None,
                skipped=True,
                skip_reason=automation_validation.reason,
                action_request_id=None,
                http_status=None,
                response_body=None,
            )

        if action_name == "confirm":
            return await self.confirm_order(session, order, event=event, trigger_mode="AUTO")

        return ActionExecutionResult(
            action_type=action_name,
            executed=False,
            success=None,
            skipped=True,
            skip_reason="ACTION_NOT_IMPLEMENTED_FOR_AUTOMATION",
            action_request_id=None,
            http_status=None,
            response_body=None,
        )

    async def confirm_order(
        self,
        session: Session,
        order: Order,
        *,
        event: OrderEventRaw | None = None,
        trigger_mode: str = "MANUAL",
    ) -> ActionExecutionResult:
        return await self._execute_http_action(
            session,
            order=order,
            action_type="confirm",
            trigger_mode=trigger_mode,
            source_event=event,
            request_payload=None,
            action_callable=lambda: self.confirm_action.execute(str(order.ifood_order_id)),
        )

    async def start_preparation(
        self,
        session: Session,
        order: Order,
        *,
        event: OrderEventRaw | None = None,
        trigger_mode: str = "MANUAL",
    ) -> ActionExecutionResult:
        return await self._execute_http_action(
            session,
            order=order,
            action_type="startPreparation",
            trigger_mode=trigger_mode,
            source_event=event,
            request_payload=None,
            action_callable=lambda: self.start_preparation_action.execute(str(order.ifood_order_id)),
        )

    async def ready_to_pickup(
        self,
        session: Session,
        order: Order,
        *,
        event: OrderEventRaw | None = None,
        trigger_mode: str = "MANUAL",
    ) -> ActionExecutionResult:
        return await self._execute_http_action(
            session,
            order=order,
            action_type="readyToPickup",
            trigger_mode=trigger_mode,
            source_event=event,
            request_payload=None,
            action_callable=lambda: self.ready_to_pickup_action.execute(str(order.ifood_order_id)),
        )

    async def dispatch(
        self,
        session: Session,
        order: Order,
        *,
        event: OrderEventRaw | None = None,
        trigger_mode: str = "MANUAL",
    ) -> ActionExecutionResult:
        return await self._execute_http_action(
            session,
            order=order,
            action_type="dispatch",
            trigger_mode=trigger_mode,
            source_event=event,
            request_payload=None,
            action_callable=lambda: self.dispatch_action.execute(str(order.ifood_order_id)),
        )

    async def get_cancellation_reasons(
        self,
        session: Session,
        order: Order,
        *,
        event: OrderEventRaw | None = None,
        trigger_mode: str = "MANUAL",
    ) -> ActionExecutionResult:
        return await self._execute_data_action(
            session,
            order=order,
            action_type="cancellationReasons",
            trigger_mode=trigger_mode,
            source_event=event,
            request_payload=None,
            action_callable=lambda: self.cancellation_reasons_action.execute(str(order.ifood_order_id)),
        )

    async def request_cancellation(
        self,
        session: Session,
        order: Order,
        payload: dict,
        *,
        event: OrderEventRaw | None = None,
        trigger_mode: str = "MANUAL",
    ) -> ActionExecutionResult:
        if not self._has_cancellation_reason(payload):
            reasons_result = await self.get_cancellation_reasons(
                session,
                order,
                event=event,
                trigger_mode=trigger_mode,
            )
            return ActionExecutionResult(
                action_type="requestCancellation",
                executed=False,
                success=False,
                skipped=True,
                skip_reason="CANCELLATION_REASON_REQUIRED",
                action_request_id=reasons_result.action_request_id,
                http_status=reasons_result.http_status,
                response_body={
                    "message": "Cancellation reason is required before requestCancellation.",
                    "cancellationReasons": reasons_result.response_body,
                },
            )

        return await self._execute_http_action(
            session,
            order=order,
            action_type="requestCancellation",
            trigger_mode=trigger_mode,
            source_event=event,
            request_payload=payload,
            action_callable=lambda: self.request_cancellation_action.execute(str(order.ifood_order_id), payload),
        )

    async def _execute_http_action(
        self,
        session: Session,
        *,
        order: Order,
        action_type: str,
        trigger_mode: str,
        source_event: OrderEventRaw | None,
        request_payload: dict[str, Any] | None,
        action_callable: Callable[[], Awaitable[httpx.Response]],
    ) -> ActionExecutionResult:
        duplicate = self._find_duplicate_action(session, order, action_type, source_event)
        if duplicate:
            logger.info(
                "Skipping duplicate order action.",
                extra={
                    "order_id": order.id,
                    "ifood_order_id": str(order.ifood_order_id),
                    "action_type": action_type,
                    "existing_action_request_id": duplicate.id,
                    "source_event_id": source_event.id if source_event else None,
                },
            )
            return ActionExecutionResult(
                action_type=action_type,
                executed=False,
                success=duplicate.success,
                skipped=True,
                skip_reason="DUPLICATE_ACTION_REQUEST",
                action_request_id=duplicate.id,
                http_status=duplicate.http_status,
                response_body=duplicate.response_body,
            )

        validation = self._validate_action_context(order, action_type)
        if not validation.allowed:
            logger.info(
                "Skipping order action due to invalid context.",
                extra={
                    "order_id": order.id,
                    "ifood_order_id": str(order.ifood_order_id),
                    "action_type": action_type,
                    "reason": validation.reason,
                    "current_status": order.current_status,
                },
            )
            return ActionExecutionResult(
                action_type=action_type,
                executed=False,
                success=False,
                skipped=True,
                skip_reason=validation.reason,
                action_request_id=None,
                http_status=None,
                response_body=None,
            )

        action_request = create_action_request(
            session,
            order=order,
            action_type=action_type,
            trigger_mode=trigger_mode,
            active_mode=self.settings.orders_active_mode,
            source_event=source_event,
            request_payload=request_payload,
        )

        try:
            response = await action_callable()
            response_body = self._parse_response_body(response)
            result_status = "ACCEPTED" if 200 <= response.status_code < 300 else "ERROR"
            success = 200 <= response.status_code < 300
            finalize_action_request(
                action_request,
                http_status=response.status_code,
                response_body=response_body,
                result_status=result_status,
                success=success,
                error_code=None if success else f"HTTP_{response.status_code}",
                error_message=None if success else response.text[:1000],
            )
            logger.info(
                "Order action executed.",
                extra={
                    "order_id": order.id,
                    "ifood_order_id": str(order.ifood_order_id),
                    "action_type": action_type,
                    "action_request_id": action_request.id,
                    "http_status": response.status_code,
                    "trigger_mode": trigger_mode,
                },
            )
            return ActionExecutionResult(
                action_type=action_type,
                executed=True,
                success=success,
                skipped=False,
                skip_reason=None,
                action_request_id=action_request.id,
                http_status=response.status_code,
                response_body=response_body,
            )
        except httpx.HTTPStatusError as exc:
            response = exc.response
            response_body = self._parse_response_body(response) if response is not None else None
            finalize_action_request(
                action_request,
                http_status=response.status_code if response is not None else None,
                response_body=response_body,
                result_status="ERROR",
                success=False,
                error_code=f"HTTP_{response.status_code}" if response is not None else "HTTP_STATUS_ERROR",
                error_message=str(exc),
            )
            logger.exception(
                "Order action failed with HTTP error.",
                extra={
                    "order_id": order.id,
                    "ifood_order_id": str(order.ifood_order_id),
                    "action_type": action_type,
                    "action_request_id": action_request.id,
                    "http_status": response.status_code if response is not None else None,
                },
            )
            return ActionExecutionResult(
                action_type=action_type,
                executed=True,
                success=False,
                skipped=False,
                skip_reason=None,
                action_request_id=action_request.id,
                http_status=response.status_code if response is not None else None,
                response_body=response_body,
            )
        except Exception as exc:
            finalize_action_request(
                action_request,
                http_status=None,
                response_body=None,
                result_status="ERROR",
                success=False,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
            )
            logger.exception(
                "Order action failed with unexpected error.",
                extra={
                    "order_id": order.id,
                    "ifood_order_id": str(order.ifood_order_id),
                    "action_type": action_type,
                    "action_request_id": action_request.id,
                },
            )
            return ActionExecutionResult(
                action_type=action_type,
                executed=True,
                success=False,
                skipped=False,
                skip_reason=None,
                action_request_id=action_request.id,
                http_status=None,
                response_body=None,
            )

    async def _execute_data_action(
        self,
        session: Session,
        *,
        order: Order,
        action_type: str,
        trigger_mode: str,
        source_event: OrderEventRaw | None,
        request_payload: dict[str, Any] | None,
        action_callable: Callable[[], Awaitable[list[dict[str, Any]]]],
    ) -> ActionExecutionResult:
        action_request = create_action_request(
            session,
            order=order,
            action_type=action_type,
            trigger_mode=trigger_mode,
            active_mode=self.settings.orders_active_mode,
            source_event=source_event,
            request_payload=request_payload,
            external_confirmation_expected=False,
        )

        try:
            response_body = await action_callable()
            finalize_action_request(
                action_request,
                http_status=200,
                response_body=response_body,
                result_status="ACCEPTED",
                success=True,
            )
            logger.info(
                "Order data action executed.",
                extra={
                    "order_id": order.id,
                    "ifood_order_id": str(order.ifood_order_id),
                    "action_type": action_type,
                    "action_request_id": action_request.id,
                },
            )
            return ActionExecutionResult(
                action_type=action_type,
                executed=True,
                success=True,
                skipped=False,
                skip_reason=None,
                action_request_id=action_request.id,
                http_status=200,
                response_body=response_body,
            )
        except Exception as exc:
            status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) and exc.response else None
            response_body = self._parse_response_body(exc.response) if isinstance(exc, httpx.HTTPStatusError) and exc.response else None
            finalize_action_request(
                action_request,
                http_status=status_code,
                response_body=response_body,
                result_status="ERROR",
                success=False,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
            )
            logger.exception(
                "Order data action failed.",
                extra={
                    "order_id": order.id,
                    "ifood_order_id": str(order.ifood_order_id),
                    "action_type": action_type,
                    "action_request_id": action_request.id,
                    "http_status": status_code,
                },
            )
            return ActionExecutionResult(
                action_type=action_type,
                executed=True,
                success=False,
                skipped=False,
                skip_reason=None,
                action_request_id=action_request.id,
                http_status=status_code,
                response_body=response_body,
            )

    @staticmethod
    def _parse_response_body(response: httpx.Response | None) -> dict[str, Any] | list[dict[str, Any]] | None:
        if response is None or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text[:2000]}

    @staticmethod
    def _has_cancellation_reason(payload: dict[str, Any]) -> bool:
        return any(
            payload.get(key)
            for key in ("reason", "reasonId", "cancellationReasonId", "cancellationCode")
        )

    @staticmethod
    def _current_status_key(order: Order) -> str:
        return extract_event_key(order.current_status, order.current_status)

    @staticmethod
    def _current_order_type(order: Order) -> str:
        return (order.order_type or "").strip().upper()

    @staticmethod
    def _current_order_timing(order: Order) -> str:
        return (order.order_timing or "").strip().upper()

    def _validate_automatic_action_context(self, order: Order, action_type: str) -> ActionContextValidation:
        order_timing = self._current_order_timing(order)
        if action_type == "confirm" and order_timing == "SCHEDULED":
            return ActionContextValidation(False, "SCHEDULED_ORDER_REQUIRES_MANUAL_CONFIRMATION")
        return ActionContextValidation(True)

    def _validate_action_context(self, order: Order, action_type: str) -> ActionContextValidation:
        status_key = self._current_status_key(order)
        order_type = self._current_order_type(order)
        if status_key in {"CONCLUDED", "CANCELLED"}:
            return ActionContextValidation(False, "ORDER_ALREADY_CLOSED")

        if action_type == "confirm" and status_key != "PLACED":
            return ActionContextValidation(False, "ORDER_STATUS_NOT_VALID_FOR_CONFIRM")
        if action_type == "startPreparation" and status_key != "CONFIRMED":
            return ActionContextValidation(False, "ORDER_STATUS_NOT_VALID_FOR_START_PREPARATION")
        if action_type == "readyToPickup" and status_key not in {"CONFIRMED", "PREPARATION_STARTED", "IN_PREPARATION", "PREPARING"}:
            return ActionContextValidation(False, "ORDER_NOT_READY_FOR_READY_TO_PICKUP")
        if action_type == "dispatch" and order_type == "TAKEOUT":
            return ActionContextValidation(False, "ORDER_TYPE_NOT_VALID_FOR_DISPATCH")
        if action_type == "dispatch" and status_key != "READY_TO_PICKUP":
            return ActionContextValidation(False, "ORDER_NOT_READY_FOR_DISPATCH")
        if action_type == "requestCancellation" and status_key in {"READY_TO_PICKUP", "DISPATCHED"}:
            return ActionContextValidation(False, "ORDER_STATUS_NOT_VALID_FOR_REQUEST_CANCELLATION")

        return ActionContextValidation(True)

    @staticmethod
    def _find_duplicate_action(
        session: Session,
        order: Order,
        action_type: str,
        source_event: OrderEventRaw | None,
    ) -> ActionRequest | None:
        query = select(ActionRequest).where(
            ActionRequest.order_id == order.id,
            ActionRequest.action_type == action_type,
        )
        if source_event is not None:
            query = query.where(ActionRequest.source_event_id == source_event.id)
        else:
            query = query.where(ActionRequest.source_event_id.is_(None))
        query = query.where(ActionRequest.result_status.in_(["PENDING", "ACCEPTED"]))

        return session.scalar(
            query.order_by(ActionRequest.id.desc())
        )


def build_action_service() -> ActionService:
    return ActionService(get_ifood_client(), get_settings())
