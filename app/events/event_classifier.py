from __future__ import annotations

from dataclasses import dataclass

FETCH_ON_EVENT_CODES = {"PLACED", "PLC"}
STATUS_KEY_ALIASES = {
    "PLC": "PLACED",
    "CFM": "CONFIRMED",
    "PRE": "PREPARATION_STARTED",
    "PRS": "PREPARATION_STARTED",
    "RTP": "READY_TO_PICKUP",
    "DSP": "DISPATCHED",
    "CON": "CONCLUDED",
    "CAN": "CANCELLED",
}
STATUS_CLASSIFICATIONS = {
    "PLACED": "ORDER_PLACED",
    "CONFIRMED": "ORDER_CONFIRMED",
    "PREPARATION_STARTED": "ORDER_IN_PREPARATION",
    "IN_PREPARATION": "ORDER_IN_PREPARATION",
    "PREPARING": "ORDER_IN_PREPARATION",
    "READY_TO_PICKUP": "ORDER_READY_TO_PICKUP",
    "DISPATCHED": "ORDER_DISPATCHED",
    "CONCLUDED": "ORDER_CONCLUDED",
    "CANCELLED": "ORDER_CANCELLED",
}


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
    if normalized_full_code:
        return normalized_full_code

    normalized_code = normalize_event_code(event_code)
    return STATUS_KEY_ALIASES.get(normalized_code, normalized_code)


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

    if normalized_full_code.startswith("NEGOTIATION.") or "CANCELLATION_REQUEST" in normalized_full_code:
        return EventClassification("ORDER_NEGOTIATION", True, True)

    if normalized_full_code.startswith("ORDER_STATUS."):
        return EventClassification(
            STATUS_CLASSIFICATIONS.get(event_key, f"ORDER_STATUS_{event_key}"),
            False,
            True,
        )

    if event_key in STATUS_CLASSIFICATIONS:
        return EventClassification(STATUS_CLASSIFICATIONS[event_key], False, True)

    return EventClassification("IGNORED", False, False)
