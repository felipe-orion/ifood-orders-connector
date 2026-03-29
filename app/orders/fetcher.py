from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.integrations.ifood_client import IfoodClient
from app.models.order_event_raw import OrderEventRaw
from app.orders.retry_policy import RetryableOrderFetchError, should_retry_order_fetch

logger = get_logger(__name__)


class OrderFetcher:
    def __init__(self, ifood_client: IfoodClient) -> None:
        self.ifood_client = ifood_client

    async def fetch_order_details(self, event: OrderEventRaw) -> dict:
        try:
            logger.info(
                "Fetching order details.",
                extra={
                    "ifood_order_id": str(event.ifood_order_id),
                    "ifood_event_id": str(event.ifood_event_id),
                },
            )
            return await self.ifood_client.get_order(str(event.ifood_order_id))
        except httpx.HTTPStatusError as exc:
            attempt_count = event.processing_state.attempt_count if event.processing_state else 0
            if exc.response is not None and should_retry_order_fetch(exc.response.status_code, attempt_count):
                logger.warning(
                    "Order details fetch will be retried.",
                    extra={
                        "ifood_order_id": str(event.ifood_order_id),
                        "ifood_event_id": str(event.ifood_event_id),
                        "status_code": exc.response.status_code,
                        "attempt_count": attempt_count,
                    },
                )
                raise RetryableOrderFetchError(str(exc)) from exc
            logger.exception(
                "Order details fetch failed with definitive error.",
                extra={
                    "ifood_order_id": str(event.ifood_order_id),
                    "ifood_event_id": str(event.ifood_event_id),
                    "status_code": exc.response.status_code if exc.response is not None else None,
                },
            )
            raise
