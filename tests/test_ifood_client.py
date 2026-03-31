from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.integrations.ifood_client import IfoodClient


class DummyTokenManager:
    async def get_valid_token(self) -> str:
        return "token"


class ScriptedIfoodClient(IfoodClient):
    def __init__(self, scripted_responses: list[httpx.Response | Exception], settings) -> None:
        super().__init__(settings, DummyTokenManager())
        self.scripted_responses = list(scripted_responses)
        self.calls: list[tuple[str, str]] = []

    async def _request(self, method: str, url: str, *, json=None, headers=None) -> httpx.Response:
        self.calls.append((method, url))
        next_item = self.scripted_responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


def _build_settings() -> SimpleNamespace:
    return SimpleNamespace(
        http_timeout_seconds=15.0,
        ifood_events_base_url="https://merchant-api.ifood.com.br/events/v1.0",
        ifood_orders_base_url="https://merchant-api.ifood.com.br/order/v1.0",
        ifood_polling_merchants=[],
        polling_retry_attempts=3,
        polling_retry_base_delay_seconds=1.0,
        orders_read_retry_attempts=3,
        orders_read_retry_base_delay_seconds=1.0,
    )


def _response(method: str, url: str, status_code: int, *, json_body=None, headers=None) -> httpx.Response:
    request = httpx.Request(method, url)
    return httpx.Response(status_code, request=request, json=json_body, headers=headers)


@pytest.mark.asyncio
async def test_get_order_retries_before_succeeding(monkeypatch) -> None:
    order_id = str(uuid4())
    url = f"https://merchant-api.ifood.com.br/order/v1.0/orders/{order_id}"
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr("app.integrations.ifood_client.asyncio.sleep", fake_sleep)

    client = ScriptedIfoodClient(
        [
            _response("GET", url, 500, json_body={"message": "temporary"}),
            _response("GET", url, 200, json_body={"id": order_id}),
        ],
        _build_settings(),
    )

    payload = await client.get_order(order_id)

    assert payload["id"] == order_id
    assert len(client.calls) == 2
    assert sleep_calls == [1.0]


@pytest.mark.asyncio
async def test_get_order_honors_retry_after_for_429(monkeypatch) -> None:
    order_id = str(uuid4())
    url = f"https://merchant-api.ifood.com.br/order/v1.0/orders/{order_id}"
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr("app.integrations.ifood_client.asyncio.sleep", fake_sleep)

    client = ScriptedIfoodClient(
        [
            _response("GET", url, 429, json_body={"message": "rate limited"}, headers={"Retry-After": "7"}),
            _response("GET", url, 200, json_body={"id": order_id}),
        ],
        _build_settings(),
    )

    payload = await client.get_order(order_id)

    assert payload["id"] == order_id
    assert len(client.calls) == 2
    assert sleep_calls == [7.0]


@pytest.mark.asyncio
async def test_get_cancellation_reasons_retries_before_succeeding(monkeypatch) -> None:
    order_id = str(uuid4())
    url = f"https://merchant-api.ifood.com.br/order/v1.0/orders/{order_id}/cancellationReasons"
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr("app.integrations.ifood_client.asyncio.sleep", fake_sleep)

    reasons = [{"id": "1", "description": "customer requested"}]
    client = ScriptedIfoodClient(
        [
            _response("GET", url, 503, json_body={"message": "temporary"}),
            _response("GET", url, 200, json_body=reasons),
        ],
        _build_settings(),
    )

    payload = await client.get_cancellation_reasons(order_id)

    assert payload == reasons
    assert len(client.calls) == 2
    assert sleep_calls == [1.0]
