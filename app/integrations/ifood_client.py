from __future__ import annotations

import asyncio
from functools import lru_cache
from time import perf_counter
from typing import Any, Callable

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.token_manager import TokenManager, get_token_manager
from app.orders.retry_policy import (
    calculate_retry_delay_seconds,
    should_retry_cancellation_reasons,
    should_retry_order_read,
)

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
        retry_on_unauthorized: bool = True,
    ) -> httpx.Response:
        token = await self.token_manager.get_valid_token()
        response = await self._request_once(
            method,
            url,
            token=token,
            json=json,
            headers=headers,
        )

        if response.status_code == 401 and retry_on_unauthorized:
            logger.warning(
                "iFood request returned 401. Forcing token refresh and retrying once.",
                extra={
                    "http_method": method,
                    "url": url,
                },
            )
            refreshed_token = await self.token_manager.force_refresh()
            logger.info(
                "Retrying iFood request after generating a new token.",
                extra={
                    "http_method": method,
                    "url": url,
                },
            )
            response = await self._request_once(
                method,
                url,
                token=refreshed_token,
                json=json,
                headers=headers,
            )

        return response

    async def _request_once(
        self,
        method: str,
        url: str,
        *,
        token: str,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
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

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        operation_name: str,
        should_retry_status: Callable[[int], bool],
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        attempts = max(self.settings.orders_read_retry_attempts, 1)
        for attempt in range(1, attempts + 1):
            try:
                response = await self._request(method, url, json=json, headers=headers)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                response = exc.response
                status_code = response.status_code if response is not None else None
                if response is None or not should_retry_status(response.status_code) or attempt >= attempts:
                    logger.exception(
                        "iFood read request failed with non-retryable or final HTTP error",
                        extra={
                            "operation": operation_name,
                            "url": url,
                            "attempt": attempt,
                            "status_code": status_code,
                        },
                    )
                    raise

                delay_seconds = calculate_retry_delay_seconds(
                    attempt,
                    self.settings.orders_read_retry_base_delay_seconds,
                    retry_after=response.headers.get("Retry-After"),
                )
                logger.warning(
                    "Retrying iFood read request after HTTP error",
                    extra={
                        "operation": operation_name,
                        "url": url,
                        "attempt": attempt,
                        "status_code": status_code,
                        "delay_seconds": delay_seconds,
                        "retry_after": response.headers.get("Retry-After"),
                    },
                )
                await asyncio.sleep(delay_seconds)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= attempts:
                    logger.exception(
                        "iFood read request failed after retries due to timeout/network error",
                        extra={
                            "operation": operation_name,
                            "url": url,
                            "attempt": attempt,
                            "error": str(exc),
                        },
                    )
                    raise

                delay_seconds = calculate_retry_delay_seconds(
                    attempt,
                    self.settings.orders_read_retry_base_delay_seconds,
                )
                logger.warning(
                    "Retrying iFood read request after timeout/network error",
                    extra={
                        "operation": operation_name,
                        "url": url,
                        "attempt": attempt,
                        "delay_seconds": delay_seconds,
                        "error": str(exc),
                    },
                )
                await asyncio.sleep(delay_seconds)

        raise RuntimeError(f"Retry loop exhausted unexpectedly for {operation_name}.")

    async def ack_events(self, event_ids: list[str]) -> httpx.Response:
        payload = [{"id": event_id} for event_id in event_ids]
        return await self._request(
            "POST",
            f"{self.settings.ifood_events_base_url}/events/acknowledgment",
            json=payload,
        )

    async def get_order(self, order_id: str) -> dict[str, Any]:
        response = await self._request_with_retry(
            "GET",
            f"{self.settings.ifood_orders_base_url}/orders/{order_id}",
            operation_name="get_order",
            should_retry_status=should_retry_order_read,
        )
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
        url = f"{self.settings.ifood_orders_base_url}/orders/{order_id}/cancellationReasons"
        attempts = max(self.settings.orders_read_retry_attempts, 1)
        for attempt in range(1, attempts + 1):
            response = await self._request("GET", url)
            if response.status_code == 204:
                return []
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                if not should_retry_cancellation_reasons(response.status_code) or attempt >= attempts:
                    logger.exception(
                        "Cancellation reasons request failed with non-retryable or final HTTP error",
                        extra={
                            "operation": "get_cancellation_reasons",
                            "url": url,
                            "attempt": attempt,
                            "status_code": response.status_code,
                        },
                    )
                    raise

                delay_seconds = calculate_retry_delay_seconds(
                    attempt,
                    self.settings.orders_read_retry_base_delay_seconds,
                    retry_after=response.headers.get("Retry-After"),
                )
                logger.warning(
                    "Retrying cancellation reasons request",
                    extra={
                        "operation": "get_cancellation_reasons",
                        "url": url,
                        "attempt": attempt,
                        "status_code": response.status_code,
                        "delay_seconds": delay_seconds,
                        "retry_after": response.headers.get("Retry-After"),
                    },
                )
                await asyncio.sleep(delay_seconds)

        return []

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
