from __future__ import annotations

from datetime import datetime, timedelta, timezone


class RetryableOrderFetchError(Exception):
    pass


def should_retry_order_fetch(status_code: int, attempt_count: int, max_attempts: int = 6) -> bool:
    return status_code == 404 and attempt_count < max_attempts


def next_retry_at(attempt_count: int) -> datetime:
    delay_seconds = min(10 * (2 ** max(attempt_count - 1, 0)), 300)
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
