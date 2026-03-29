from __future__ import annotations

import httpx
from datetime import datetime, timezone
from typing import Callable

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.actions.action_service import build_action_service
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.events.ack_service import acknowledge_events
from app.events.dedup_service import list_processable_events
from app.events.event_processor import EventProcessingResult, EventProcessor
from app.events.ordering_service import sort_events_by_created_at
from app.events.persistence_service import create_polling_run, store_polled_events
from app.integrations.ifood_client import IfoodClient, PollingApiResult, get_ifood_client
from app.models.event_polling_run import EventPollingRun
from app.orders.fetcher import OrderFetcher
from app.orders.order_service import OrderService

logger = get_logger(__name__)


class PollingResult(BaseModel):
    polling_run_id: int | None = None
    http_status: int | None = None
    response_event_count: int = 0
    new_event_count: int = 0
    duplicate_event_count: int = 0
    acknowledged_event_count: int = 0
    processable_event_count: int = 0
    processed_event_count: int = 0
    failed_event_count: int = 0
    ack_success: bool | None = None
    finished_at: datetime | None = None


class PollingService:
    def __init__(
        self,
        ifood_client: IfoodClient,
        *,
        session_factory: Callable[[], Session] = SessionLocal,
        event_processor: EventProcessor | None = None,
    ) -> None:
        self.ifood_client = ifood_client
        self.session_factory = session_factory
        self.order_service = OrderService(OrderFetcher(ifood_client))
        self.event_processor = event_processor or EventProcessor(
            self.order_service,
            build_action_service(),
        )

    async def poll_once(self) -> PollingResult:
        logger.info("Starting polling cycle.")

        polling_run_id: int | None = None
        polling_api_result: PollingApiResult | None = None
        persistence_result = None

        with self.session_factory() as session:
            polling_run = create_polling_run(session)
            polling_run_id = polling_run.id
            try:
                polling_api_result = await self.ifood_client.get_events()
                polling_run.http_status = polling_api_result.status_code
                persistence_result = store_polled_events(session, polling_run, polling_api_result.events)
                session.commit()
                logger.info(
                    "Polling persistence completed.",
                    extra={
                        "polling_run_id": polling_run.id,
                        "http_status": polling_run.http_status,
                        "received_event_count": len(polling_api_result.events),
                        "new_event_count": persistence_result.new_event_count,
                        "duplicate_event_count": persistence_result.duplicate_event_count,
                    },
                )
            except httpx.HTTPStatusError as exc:
                polling_run.http_status = exc.response.status_code if exc.response is not None else None
                polling_run.error_message = str(exc)
                polling_run.finished_at = datetime.now(timezone.utc)
                session.commit()
                logger.exception(
                    "Polling cycle failed during fetch/persistence.",
                    extra={
                        "polling_run_id": polling_run.id,
                        "http_status": polling_run.http_status,
                        "error": str(exc),
                    },
                )
                raise
            except Exception as exc:
                polling_run.error_message = str(exc)
                polling_run.finished_at = datetime.now(timezone.utc)
                session.commit()
                logger.exception(
                    "Polling cycle failed before acknowledgment.",
                    extra={"polling_run_id": polling_run.id, "error": str(exc)},
                )
                raise

        assert polling_run_id is not None
        assert polling_api_result is not None
        assert persistence_result is not None

        with self.session_factory() as session:
            polling_run = session.get(EventPollingRun, polling_run_id)
            ack_result = await acknowledge_events(session, self.ifood_client, polling_run, polling_api_result.events)
            session.commit()
            logger.info(
                "Acknowledgment completed.",
                extra={
                    "polling_run_id": polling_run.id,
                    "ack_success": ack_result.success,
                    "acknowledged_event_count": ack_result.acknowledged_event_count,
                    "ack_http_status": ack_result.status_code,
                },
            )

        with self.session_factory() as session:
            polling_run = session.get(EventPollingRun, polling_run_id)
            processable_events = list_processable_events(session)
            ordered_events = sort_events_by_created_at(processable_events)

            processed_count = 0
            failed_count = 0
            processable_count = len(ordered_events)
            for event in ordered_events:
                try:
                    result = await self.event_processor.process_event(session, event)
                    session.commit()
                    processed_count += 1
                    self._log_event_processed(result, polling_run_id)
                except Exception as exc:  # pragma: no cover - defensive
                    session.commit()
                    failed_count += 1
                    logger.exception(
                        "Failed to process event.",
                        extra={
                            "polling_run_id": polling_run_id,
                            "ifood_event_id": str(event.ifood_event_id),
                            "ifood_order_id": str(event.ifood_order_id),
                            "error": str(exc),
                        },
                    )

            polling_run.finished_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(
                "Polling cycle finished.",
                extra={
                    "polling_run_id": polling_run.id,
                    "http_status": polling_run.http_status,
                    "received_event_count": len(polling_api_result.events),
                    "new_event_count": persistence_result.new_event_count,
                    "duplicate_event_count": persistence_result.duplicate_event_count,
                    "ack_success": ack_result.success,
                    "acknowledged_event_count": ack_result.acknowledged_event_count,
                    "processable_event_count": processable_count,
                    "processed_event_count": processed_count,
                    "failed_event_count": failed_count,
                },
            )

            return PollingResult(
                polling_run_id=polling_run.id,
                http_status=polling_run.http_status,
                response_event_count=len(polling_api_result.events),
                new_event_count=persistence_result.new_event_count,
                duplicate_event_count=persistence_result.duplicate_event_count,
                acknowledged_event_count=ack_result.acknowledged_event_count,
                processable_event_count=processable_count,
                processed_event_count=processed_count,
                failed_event_count=failed_count,
                ack_success=ack_result.success,
                finished_at=polling_run.finished_at,
            )

    @staticmethod
    def _log_event_processed(result: EventProcessingResult, polling_run_id: int) -> None:
        logger.info(
            "Event processed.",
            extra={
                "polling_run_id": polling_run_id,
                "ifood_event_id": result.event_id,
                "ifood_order_id": result.order_id,
                "classification": result.classification,
                "processing_status": result.processing_status,
                "requires_order_fetch": result.requires_order_fetch,
                "updates_status": result.updates_status,
                "suggested_action": result.suggested_action,
                "action_executed": result.action_executed,
                "action_success": result.action_success,
                "action_skipped": result.action_skipped,
                "action_skip_reason": result.action_skip_reason,
            },
        )


def build_polling_service() -> PollingService:
    return PollingService(get_ifood_client())
