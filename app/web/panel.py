from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import String, cast, desc, func, select, text
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.events.polling_service import build_polling_service
from app.events.event_classifier import extract_event_key
from app.models.action_request import ActionRequest
from app.models.event_polling_run import EventPollingRun
from app.models.event_processing_state import EventProcessingState
from app.models.order import Order
from app.models.order_event_raw import OrderEventRaw
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _base_context(request: Request, *, title: str, active_page: str, **extra: Any) -> dict[str, Any]:
    settings = get_settings()
    return {
        "request": request,
        "title": title,
        "active_page": active_page,
        "settings": settings,
        **extra,
    }


def _parse_order_uuid(order_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid order_id. Expected UUID.") from exc


def _serialize_polling_run(session, run: EventPollingRun) -> dict[str, Any]:
    processed_event_count = session.scalar(
        select(func.count(OrderEventRaw.id))
        .join(EventProcessingState, EventProcessingState.order_event_id == OrderEventRaw.id)
        .where(
            OrderEventRaw.first_polling_run_id == run.id,
            EventProcessingState.processing_status == "PROCESSED",
        )
    ) or 0
    failed_event_count = session.scalar(
        select(func.count(OrderEventRaw.id))
        .join(EventProcessingState, EventProcessingState.order_event_id == OrderEventRaw.id)
        .where(
            OrderEventRaw.first_polling_run_id == run.id,
            EventProcessingState.processing_status == "FAILED",
        )
    ) or 0
    retry_event_count = session.scalar(
        select(func.count(OrderEventRaw.id))
        .join(EventProcessingState, EventProcessingState.order_event_id == OrderEventRaw.id)
        .where(
            OrderEventRaw.first_polling_run_id == run.id,
            EventProcessingState.processing_status == "RETRY",
        )
    ) or 0

    return {
        "id": run.id,
        "http_status": run.http_status,
        "response_event_count": run.response_event_count,
        "new_event_count": run.new_event_count,
        "duplicate_event_count": run.duplicate_event_count,
        "processed_event_count": processed_event_count,
        "failed_event_count": failed_event_count,
        "retry_event_count": retry_event_count,
        "ack_success": run.ack_success,
        "error_message": run.error_message,
        "finished_at": run.finished_at,
        "started_at": run.started_at,
    }


def _serialize_order_row(order: Order) -> dict[str, Any]:
    return {
        "ifood_order_id": str(order.ifood_order_id),
        "current_status": order.current_status,
        "order_type": order.order_type,
        "order_timing": order.order_timing,
        "category": order.category,
        "placed_at": order.placed_at,
        "last_synced_at": order.last_synced_at,
    }


def _serialize_order_detail(order: Order) -> dict[str, Any]:
    status_key = _status_key(order.current_status)
    order_type_key = (order.order_type or "").strip().upper()
    return {
        "id": order.id,
        "ifood_order_id": str(order.ifood_order_id),
        "display_id": order.display_id,
        "merchant_id": order.merchant_id,
        "current_status": order.current_status,
        "status_key": status_key,
        "status_badge_class": _status_badge_class(status_key),
        "sales_channel": order.sales_channel,
        "category": order.category,
        "category_badge_class": _category_badge_class(order.category),
        "order_type": order.order_type,
        "order_type_badge_class": _order_type_badge_class(order_type_key),
        "order_timing": order.order_timing,
        "currency": order.currency,
        "subtotal_amount": order.subtotal_amount,
        "delivery_fee_amount": order.delivery_fee_amount,
        "benefits_amount": order.benefits_amount,
        "additional_fees_amount": order.additional_fees_amount,
        "total_amount": order.total_amount,
        "customer_notes": order.customer_notes,
        "placed_at": order.placed_at,
        "confirmed_at": order.confirmed_at,
        "preparation_start_at": order.preparation_start_at,
        "ready_to_pickup_at": order.ready_to_pickup_at,
        "dispatched_at": order.dispatched_at,
        "concluded_at": order.concluded_at,
        "cancelled_at": order.cancelled_at,
        "latest_event_created_at": order.latest_event_created_at,
        "last_synced_at": order.last_synced_at,
        "customer": None
        if not order.customer
        else {
            "name": order.customer.name,
            "document_number": order.customer.document_number,
            "phone_number": order.customer.phone_number,
            "phone_localizer": order.customer.phone_localizer,
            "phone_localizer_expiration": order.customer.phone_localizer_expiration,
            "segmentation": order.customer.segmentation,
        },
        "delivery": None
        if not order.delivery
        else {
            "delivery_mode": order.delivery.delivery_mode,
            "delivered_by": order.delivery.delivered_by,
            "pickup_code": order.delivery.pickup_code,
            "delivery_datetime": order.delivery.delivery_datetime,
            "takeout_datetime": order.delivery.takeout_datetime,
            "schedule_start_at": order.delivery.schedule_start_at,
            "schedule_end_at": order.delivery.schedule_end_at,
            "address_street": order.delivery.address_street,
            "address_number": order.delivery.address_number,
            "address_complement": order.delivery.address_complement,
            "address_neighborhood": order.delivery.address_neighborhood,
            "address_city": order.delivery.address_city,
            "address_state": order.delivery.address_state,
            "postal_code": order.delivery.postal_code,
        },
        "items": [
            {
                "item_sequence": item.item_sequence,
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "observations": item.observations,
                "unit_price_amount": item.unit_price_amount,
                "options_price_amount": item.options_price_amount,
                "total_price_amount": item.total_price_amount,
                "options": [
                    {
                        "option_sequence": option.option_sequence,
                        "name": option.name,
                        "quantity": option.quantity,
                        "group_name": option.group_name,
                        "unit_price_amount": option.unit_price_amount,
                        "total_price_amount": option.total_price_amount,
                    }
                    for option in item.options
                ],
            }
            for item in order.items
        ],
        "payments": [
            {
                "payment_sequence": payment.payment_sequence,
                "method": payment.method,
                "payment_type": payment.payment_type,
                "prepaid": payment.prepaid,
                "currency": payment.currency,
                "amount": payment.amount,
                "change_for_amount": payment.change_for_amount,
                "card_brand": payment.card_brand,
                "authorization_code": payment.authorization_code,
                "acquirer_document": payment.acquirer_document,
            }
            for payment in order.payments
        ],
        "benefits": [
            {
                "benefit_sequence": benefit.benefit_sequence,
                "benefit_type": benefit.benefit_type,
                "description": benefit.description,
                "campaign_name": benefit.campaign_name,
                "amount": benefit.amount,
                "sponsorship_values_json": benefit.sponsorship_values_json,
            }
            for benefit in order.benefits
        ],
        "ui": _build_action_controls(status_key, order_type_key),
    }


def _status_key(status_value: str | None) -> str:
    return extract_event_key(status_value, status_value)


def _status_badge_class(status_key: str) -> str:
    return {
        "PLACED": "status-placed",
        "CONFIRMED": "status-confirmed",
        "PREPARATION_STARTED": "status-preparing",
        "IN_PREPARATION": "status-preparing",
        "PREPARING": "status-preparing",
        "READY_TO_PICKUP": "status-ready",
        "DISPATCHED": "status-dispatched",
        "CANCELLED": "status-cancelled",
        "CONCLUDED": "status-concluded",
    }.get(status_key, "status-default")


def _order_type_badge_class(order_type: str) -> str:
    return {
        "DELIVERY": "type-delivery",
        "TAKEOUT": "type-takeout",
        "DINE_IN": "type-dinein",
    }.get(order_type, "type-default")


def _category_badge_class(category: str | None) -> str:
    return "category-badge" if category else "category-badge muted-badge"


def _build_action_controls(status_key: str, order_type: str) -> dict[str, Any]:
    can_cancel = status_key in {"PLACED", "CONFIRMED", "PREPARATION_STARTED", "IN_PREPARATION", "PREPARING"}
    return {
        "show_confirm": status_key == "PLACED",
        "show_start_preparation": status_key == "CONFIRMED",
        "show_ready": status_key in {"PREPARATION_STARTED", "IN_PREPARATION", "PREPARING"},
        "show_dispatch": status_key == "READY_TO_PICKUP" and order_type == "DELIVERY",
        "show_reason_lookup": can_cancel,
        "show_cancel": can_cancel,
        "view_only": status_key in {"DISPATCHED", "CONCLUDED", "CANCELLED"} or (status_key == "READY_TO_PICKUP" and order_type != "DELIVERY"),
        "status_key": status_key,
        "order_type": order_type,
    }


def _serialize_status_history(item: OrderStatusHistory) -> dict[str, Any]:
    return {
        "status_full_code": item.status_full_code,
        "status_code": item.status_code,
        "occurred_at": item.occurred_at,
        "recorded_at": item.recorded_at,
        "source": item.source,
        "notes": item.notes,
    }


def _serialize_action(item: ActionRequest) -> dict[str, Any]:
    return {
        "action_type": item.action_type,
        "trigger_mode": item.trigger_mode,
        "active_mode": item.active_mode,
        "result_status": item.result_status,
        "success": item.success,
        "http_status": item.http_status,
        "request_sent_at": item.request_sent_at,
        "response_received_at": item.response_received_at,
        "request_payload": item.request_payload,
        "response_body": item.response_body,
        "error_message": item.error_message,
    }


def _serialize_event(item: OrderEventRaw) -> dict[str, Any]:
    state = item.processing_state
    return {
        "ifood_event_id": str(item.ifood_event_id),
        "ifood_order_id": str(item.ifood_order_id),
        "event_code": item.event_code,
        "event_full_code": item.event_full_code,
        "event_created_at": item.event_created_at,
        "receive_count": item.receive_count,
        "processing_status": state.processing_status if state else None,
        "classified_as": state.classified_as if state else None,
        "attempt_count": state.attempt_count if state else None,
        "last_error_message": state.last_error_message if state else None,
    }


@router.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/panel", status_code=303)


@router.get("/panel")
def panel_dashboard(request: Request) -> Any:
    settings = get_settings()
    with SessionLocal() as session:
        db_status = "up"
        try:
            session.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - defensive
            db_status = f"down: {exc}"

        latest_run = session.scalar(select(EventPollingRun).order_by(EventPollingRun.id.desc()).limit(1))
        recent_runs = list(session.scalars(select(EventPollingRun).order_by(EventPollingRun.id.desc()).limit(10)))
        recent_events = list(
            session.scalars(
                select(OrderEventRaw)
                .options(selectinload(OrderEventRaw.processing_state))
                .order_by(OrderEventRaw.event_created_at.desc(), OrderEventRaw.id.desc())
                .limit(10)
            )
        )

        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_failure_count = session.scalar(
            select(func.count(EventProcessingState.id)).where(
                EventProcessingState.processing_status.in_(["FAILED", "RETRY"]),
                EventProcessingState.updated_at >= recent_cutoff,
            )
        ) or 0
        recent_event_count = session.scalar(
            select(func.count(OrderEventRaw.id)).where(OrderEventRaw.first_received_at >= recent_cutoff)
        ) or 0

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=_base_context(
                request,
                title="Dashboard Operacional",
                active_page="dashboard",
                api_status="ok",
                db_status=db_status,
                latest_run=_serialize_polling_run(session, latest_run) if latest_run else None,
                recent_runs=[_serialize_polling_run(session, run) for run in recent_runs],
                recent_failure_count=recent_failure_count,
                recent_event_count=recent_event_count,
                recent_events=[_serialize_event(item) for item in recent_events],
                polling_message=request.query_params.get("polling_message"),
                polling_status=request.query_params.get("polling_status"),
                scheduler_enabled=settings.scheduler_enabled,
                polling_interval_seconds=settings.polling_interval_seconds,
            ),
        )


@router.post("/panel/polling/run-once")
async def panel_run_polling_once() -> RedirectResponse:
    try:
        result = await build_polling_service().poll_once()
        message = (
            f"Polling executado. run_id={result.polling_run_id}, "
            f"http_status={result.http_status}, processed={result.processed_event_count}"
        )
        query = urlencode({"polling_status": "success", "polling_message": message})
        return RedirectResponse(url=f"/panel?{query}", status_code=303)
    except Exception as exc:  # pragma: no cover - defensive
        query = urlencode({"polling_status": "error", "polling_message": str(exc)})
        return RedirectResponse(url=f"/panel?{query}", status_code=303)


@router.get("/panel/orders")
def panel_orders(
    request: Request,
    q: str = "",
    status: str = "",
    order_type: str = "",
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    with SessionLocal() as session:
        query = select(Order).order_by(Order.last_synced_at.desc(), Order.id.desc())
        if q:
            query = query.where(cast(Order.ifood_order_id, String).ilike(f"%{q.strip()}%"))
        if status:
            query = query.where(Order.current_status == status.strip())
        if order_type:
            query = query.where(Order.order_type == order_type.strip())

        orders = list(session.scalars(query.limit(limit)))
        available_statuses = list(
            session.scalars(select(Order.current_status).distinct().order_by(Order.current_status.asc()))
        )
        available_types = list(
            session.scalars(select(Order.order_type).where(Order.order_type.is_not(None)).distinct().order_by(Order.order_type.asc()))
        )

        return templates.TemplateResponse(
            request=request,
            name="orders.html",
            context=_base_context(
                request,
                title="Pedidos",
                active_page="orders",
                orders=[_serialize_order_row(order) for order in orders],
                filters={"q": q, "status": status, "order_type": order_type, "limit": limit},
                available_statuses=available_statuses,
                available_types=available_types,
            ),
        )


@router.get("/panel/orders/{order_id}")
def panel_order_detail(request: Request, order_id: str) -> Any:
    order_uuid = _parse_order_uuid(order_id)
    with SessionLocal() as session:
        order = session.scalar(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.delivery),
                selectinload(Order.items).selectinload(OrderItem.options),
                selectinload(Order.payments),
                selectinload(Order.benefits),
            )
            .where(Order.ifood_order_id == order_uuid)
        )
        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        status_history = list(
            session.scalars(
                select(OrderStatusHistory)
                .where(OrderStatusHistory.order_id == order.id)
                .order_by(desc(OrderStatusHistory.occurred_at), desc(OrderStatusHistory.id))
            )
        )
        actions = list(
            session.scalars(
                select(ActionRequest)
                .where(ActionRequest.order_id == order.id)
                .order_by(desc(ActionRequest.request_sent_at), desc(ActionRequest.id))
                .limit(20)
            )
        )
        events = list(
            session.scalars(
                select(OrderEventRaw)
                .options(selectinload(OrderEventRaw.processing_state))
                .where(OrderEventRaw.ifood_order_id == order_uuid)
                .order_by(desc(OrderEventRaw.event_created_at), desc(OrderEventRaw.id))
                .limit(50)
            )
        )

        return templates.TemplateResponse(
            request=request,
            name="order_detail.html",
            context=_base_context(
                request,
                title=f"Pedido {order.display_id or order.ifood_order_id}",
                active_page="orders",
                order=_serialize_order_detail(order),
                status_history=[_serialize_status_history(item) for item in status_history],
                actions=[_serialize_action(item) for item in actions],
                events=[_serialize_event(item) for item in events],
            ),
        )


@router.get("/panel/events")
def panel_events(
    request: Request,
    order_id: str = "",
    processing_status: str = "",
    limit: int = Query(default=100, ge=1, le=300),
) -> Any:
    with SessionLocal() as session:
        query = (
            select(OrderEventRaw)
            .options(selectinload(OrderEventRaw.processing_state))
            .order_by(desc(OrderEventRaw.event_created_at), desc(OrderEventRaw.id))
        )
        if order_id:
            query = query.where(cast(OrderEventRaw.ifood_order_id, String).ilike(f"%{order_id.strip()}%"))
        if processing_status:
            query = query.join(OrderEventRaw.processing_state).where(
                EventProcessingState.processing_status == processing_status.strip()
            )

        events = list(session.scalars(query.limit(limit)))
        statuses = list(
            session.scalars(
                select(EventProcessingState.processing_status).distinct().order_by(EventProcessingState.processing_status.asc())
            )
        )

        return templates.TemplateResponse(
            request=request,
            name="events.html",
            context=_base_context(
                request,
                title="Eventos",
                active_page="events",
                events=[_serialize_event(item) for item in events],
                filters={"order_id": order_id, "processing_status": processing_status, "limit": limit},
                available_processing_statuses=statuses,
            ),
        )


@router.get("/panel/polling")
def panel_polling_runs(request: Request) -> Any:
    with SessionLocal() as session:
        runs = list(session.scalars(select(EventPollingRun).order_by(desc(EventPollingRun.id)).limit(30)))
        return templates.TemplateResponse(
            request=request,
            name="polling_runs.html",
            context=_base_context(
                request,
                title="Polling Runs",
                active_page="polling",
                runs=[_serialize_polling_run(session, run) for run in runs],
            ),
        )
