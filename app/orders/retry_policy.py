from __future__ import annotations

from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone


class RetryableOrderFetchError(Exception):
    pass


def should_retry_order_fetch(status_code: int, attempt_count: int, max_attempts: int = 6) -> bool:
    return status_code == 404 and attempt_count < max_attempts


def should_retry_order_read(status_code: int) -> bool:
    return status_code in {404, 408, 425, 429} or status_code >= 500


def should_retry_cancellation_reasons(status_code: int) -> bool:
    return status_code in {408, 425, 429} or status_code >= 500


def parse_retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    try:
        return max(float(stripped), 0.0)
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(stripped)
    except (TypeError, ValueError, IndexError):
        return None

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)

    return max((retry_at - datetime.now(timezone.utc)).total_seconds(), 0.0)


def calculate_retry_delay_seconds(
    attempt: int,
    base_delay_seconds: float,
    *,
    retry_after: str | None = None,
    max_delay_seconds: float = 60.0,
) -> float:
    retry_after_seconds = parse_retry_after_seconds(retry_after)
    if retry_after_seconds is not None:
        return retry_after_seconds

    exponential_delay = base_delay_seconds * (2 ** max(attempt - 1, 0))
    return min(exponential_delay, max_delay_seconds)


def next_retry_at(attempt_count: int) -> datetime:
    delay_seconds = min(10 * (2 ** max(attempt_count - 1, 0)), 300)
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
