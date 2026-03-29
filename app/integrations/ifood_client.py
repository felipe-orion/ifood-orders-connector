from __future__ import annotations

import asyncio
from functools import lru_cache
from time import perf_counter
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.token_manager import TokenManager, get_token_manager

logger = get_logger(__name__)


class PollingApiResult:
    def __init__(self, status_code: int, events: list[dict[str, Any]]) -> None:
        self.status_code = status_code
        self.events = events


class IfoodClient:
    def __init__(self, settings: Settings, token_manager: TokenManager) -> None:
        self.settings = settings
        self.token_manager = token_manager

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        token = await self.token_manager.get_valid_token()
        request_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)

        safe_headers = {
            key: ("***" if key.lower() == "authorization" else value)
            for key, value in request_headers.items()
        }
        logger.info(
            "iFood request",
            extra={
                "http_method": method,
                "url": url,
                "headers": safe_headers,
                "payload": json,
            },
        )

        started = perf_counter()
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            try:
                response = await client.request(method=method, url=url, headers=request_headers, json=json)
            except httpx.HTTPError as exc:
                logger.exception(
                    "iFood HTTP error",
                    extra={
                        "http_method": method,
                        "url": url,
                        "payload": json,
                        "error": str(exc),
                    },
                )
                raise

        duration_ms = round((perf_counter() - started) * 1000)
        logger.info(
            "iFood response",
            extra={
                "http_method": method,
                "url": url,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "response_body": response.text[:2000],
            },
        )
        return response

    async def get_events(self) -> PollingApiResult:
        polling_headers: dict[str, str] = {}
        if self.settings.ifood_polling_merchants:
            polling_headers["x-polling-merchants"] = ",".join(self.settings.ifood_polling_merchants)

        attempts = max(self.settings.polling_retry_attempts, 1)
        for attempt in range(1, attempts + 1):
            try:
                response = await self._request(
                    "GET",
                    f"{self.settings.ifood_events_base_url}/events:polling",
                    headers=polling_headers or None,
                )
                if response.status_code == 204:
                    return PollingApiResult(status_code=response.status_code, events=[])
                response.raise_for_status()
                return PollingApiResult(status_code=response.status_code, events=response.json())
            except httpx.HTTPStatusError as exc:
                if not self._should_retry_polling(exc.response.status_code) or attempt >= attempts:
                    logger.exception(
                        "Polling failed with non-retryable or final HTTP error",
                        extra={"attempt": attempt, "status_code": exc.response.status_code},
                    )
                    raise
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= attempts:
                    logger.exception(
                        "Polling failed after retries due to timeout/network error",
                        extra={"attempt": attempt, "error": str(exc)},
                    )
                    raise

            delay = self.settings.polling_retry_base_delay_seconds * attempt
            logger.warning(
                "Retrying polling request",
                extra={"attempt": attempt, "delay_seconds": delay},
            )
            await asyncio.sleep(delay)

        return PollingApiResult(status_code=204, events=[])

    async def ack_events(self, event_ids: list[str]) -> httpx.Response:
        payload = [{"id": event_id} for event_id in event_ids]
        return await self._request(
            "POST",
            f"{self.settings.ifood_events_base_url}/events/acknowledgment",
            json=payload,
        )

    async def get_order(self, order_id: str) -> dict[str, Any]:
        response = await self._request("GET", f"{self.settings.ifood_orders_base_url}/orders/{order_id}")
        response.raise_for_status()
        return response.json()

    async def confirm_order(self, order_id: str) -> httpx.Response:
        return await self._request("POST", f"{self.settings.ifood_orders_base_url}/orders/{order_id}/confirm")

    async def start_preparation(self, order_id: str) -> httpx.Response:
        return await self._request(
            "POST",
            f"{self.settings.ifood_orders_base_url}/orders/{order_id}/startPreparation",
        )

    async def ready_to_pickup(self, order_id: str) -> httpx.Response:
        return await self._request(
            "POST",
            f"{self.settings.ifood_orders_base_url}/orders/{order_id}/readyToPickup",
        )

    async def dispatch_order(self, order_id: str) -> httpx.Response:
        return await self._request("POST", f"{self.settings.ifood_orders_base_url}/orders/{order_id}/dispatch")

    async def get_cancellation_reasons(self, order_id: str) -> list[dict[str, Any]]:
        response = await self._request(
            "GET",
            f"{self.settings.ifood_orders_base_url}/orders/{order_id}/cancellationReasons",
        )
        if response.status_code == 204:
            return []
        response.raise_for_status()
        return response.json()

    async def request_cancellation(self, order_id: str, payload: dict[str, Any]) -> httpx.Response:
        return await self._request(
            "POST",
            f"{self.settings.ifood_orders_base_url}/orders/{order_id}/requestCancellation",
            json=payload,
        )

    @staticmethod
    def _should_retry_polling(status_code: int) -> bool:
        return status_code == 429 or status_code >= 500


@lru_cache(maxsize=1)
def get_ifood_client() -> IfoodClient:
    return IfoodClient(get_settings(), get_token_manager())
