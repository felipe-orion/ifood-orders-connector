from __future__ import annotations

from dataclasses import dataclass

FETCH_ON_EVENT_CODES = {"PLACED", "PLC"}


@dataclass(frozen=True)
class EventClassification:
    classification: str
    requires_order_fetch: bool
    updates_status: bool
    auto_action: str | None = None


def normalize_event_code(event_code: str | None) -> str:
    return (event_code or "").strip().upper()


def normalize_event_full_code(event_full_code: str | None) -> str:
    return (event_full_code or "").strip().upper()


def extract_event_key(event_code: str | None, event_full_code: str | None) -> str:
    normalized_full_code = normalize_event_full_code(event_full_code)
    if normalized_full_code and "." in normalized_full_code:
        return normalized_full_code.split(".")[-1]

    normalized_code = normalize_event_code(event_code)
    return normalized_code


def classify_event(event_code: str, event_full_code: str) -> EventClassification:
    normalized_code = normalize_event_code(event_code)
    normalized_full_code = normalize_event_full_code(event_full_code)
    event_key = extract_event_key(normalized_code, normalized_full_code)
    values = {normalized_code, normalized_full_code, event_key}

    if values & FETCH_ON_EVENT_CODES:
        return EventClassification(
            classification="ORDER_PLACED",
            requires_order_fetch=True,
            updates_status=True,
            auto_action="confirm",
        )

    if values & {"CONFIRMED", "CFM"}:
        return EventClassification("ORDER_CONFIRMED", False, True)
    if values & {"READY_TO_PICKUP", "RTP"}:
        return EventClassification("ORDER_READY_TO_PICKUP", False, True)
    if values & {"DISPATCHED", "DSP"}:
        return EventClassification("ORDER_DISPATCHED", False, True)
    if values & {"CONCLUDED", "CON"}:
        return EventClassification("ORDER_CONCLUDED", False, True)
    if values & {"CANCELLED", "CAN"}:
        return EventClassification("ORDER_CANCELLED", False, True)
    if normalized_full_code.startswith("CANCELLATION_REQUEST"):
        return EventClassification("CANCELLATION_REQUEST", False, False)

    return EventClassification("IGNORED", False, False)
