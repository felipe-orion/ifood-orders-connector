from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.actions.action_service import ActionExecutionResult, build_action_service
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.events.polling_service import build_polling_service
from app.models.order import Order

router = APIRouter()


class InternalOrderSummary(BaseModel):
    id: int
    ifood_order_id: str
    current_status: str
    merchant_id: int
    sales_channel: str | None
    order_type: str | None
    order_timing: str | None
    last_synced_at: str


def _load_order_or_404(session: Session, ifood_order_id: str) -> Order:
    try:
        order_uuid = uuid.UUID(ifood_order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid order_id. Expected UUID.") from exc

    order = session.scalar(select(Order).where(Order.ifood_order_id == order_uuid))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found in local database.")
    return order


def _to_order_summary(order: Order) -> InternalOrderSummary:
    return InternalOrderSummary(
        id=order.id,
        ifood_order_id=str(order.ifood_order_id),
        current_status=order.current_status,
        merchant_id=order.merchant_id,
        sales_channel=order.sales_channel,
        order_type=order.order_type,
        order_timing=order.order_timing,
        last_synced_at=order.last_synced_at.isoformat(),
    )


def _serialize_action_result(result: ActionExecutionResult) -> dict[str, Any]:
    return {
        "action_type": result.action_type,
        "executed": result.executed,
        "success": result.success,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
        "action_request_id": result.action_request_id,
        "http_status": result.http_status,
        "response_body": result.response_body,
    }


@router.get("/config")
def read_runtime_config() -> dict[str, Any]:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "orders_active_mode": settings.orders_active_mode,
        "enabled_automatic_actions": sorted(settings.enabled_automatic_actions),
        "scheduler_enabled": settings.scheduler_enabled,
        "polling_interval_seconds": settings.polling_interval_seconds,
        "polling_retry_attempts": settings.polling_retry_attempts,
        "ifood_events_base_url": settings.ifood_events_base_url,
        "ifood_orders_base_url": settings.ifood_orders_base_url,
        "ifood_polling_merchants": settings.ifood_polling_merchants,
    }


@router.post("/polling/run-once")
async def run_polling_once() -> dict[str, Any]:
    service = build_polling_service()
    try:
        result = await service.poll_once()
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result.model_dump()


@router.get("/orders/{order_id}")
def read_local_order(order_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        order = _load_order_or_404(session, order_id)
        return {"order": _to_order_summary(order).model_dump()}


@router.post("/actions/{order_id}/confirm")
async def confirm_order(order_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        order = _load_order_or_404(session, order_id)
        result = await build_action_service().confirm_order(session, order)
        session.commit()
        return _serialize_action_result(result)


@router.post("/actions/{order_id}/start-preparation")
async def start_preparation(order_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        order = _load_order_or_404(session, order_id)
        result = await build_action_service().start_preparation(session, order)
        session.commit()
        return _serialize_action_result(result)


@router.post("/actions/{order_id}/ready-to-pickup")
async def ready_to_pickup(order_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        order = _load_order_or_404(session, order_id)
        result = await build_action_service().ready_to_pickup(session, order)
        session.commit()
        return _serialize_action_result(result)


@router.post("/actions/{order_id}/dispatch")
async def dispatch_order(order_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        order = _load_order_or_404(session, order_id)
        result = await build_action_service().dispatch(session, order)
        session.commit()
        return _serialize_action_result(result)


@router.get("/actions/{order_id}/cancellation-reasons")
async def get_cancellation_reasons(order_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        order = _load_order_or_404(session, order_id)
        result = await build_action_service().get_cancellation_reasons(session, order)
        session.commit()
        return _serialize_action_result(result)


@router.post("/actions/{order_id}/request-cancellation")
async def request_cancellation(order_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    with SessionLocal() as session:
        order = _load_order_or_404(session, order_id)
        result = await build_action_service().request_cancellation(session, order, payload)
        session.commit()
        return _serialize_action_result(result)
