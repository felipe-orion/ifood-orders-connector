from app.events.event_classifier import classify_event, extract_event_key


def test_extract_event_key_from_full_code() -> None:
    assert extract_event_key("RTP", "ORDER_STATUS.READY_TO_PICKUP") == "READY_TO_PICKUP"


def test_classify_placed_event_enables_fetch_and_confirm() -> None:
    classification = classify_event("PLC", "ORDER_STATUS.PLACED")

    assert classification.classification == "ORDER_PLACED"
    assert classification.requires_order_fetch is True
    assert classification.auto_action == "confirm"


def test_classify_generic_order_status_event_updates_status() -> None:
    classification = classify_event("UNK", "ORDER_STATUS.PREPARATION_STARTED")

    assert classification.classification == "ORDER_IN_PREPARATION"
    assert classification.requires_order_fetch is False
    assert classification.updates_status is True


def test_classify_preparation_started_without_prefix_updates_status() -> None:
    classification = classify_event("PRS", "PREPARATION_STARTED")

    assert classification.classification == "ORDER_IN_PREPARATION"
    assert classification.requires_order_fetch is False
    assert classification.updates_status is True


def test_classify_preparing_alias_without_prefix_updates_status() -> None:
    classification = classify_event("UNK", "PREPARING")

    assert classification.classification == "ORDER_IN_PREPARATION"
    assert classification.requires_order_fetch is False
    assert classification.updates_status is True


def test_classify_negotiation_event_requires_fetch() -> None:
    classification = classify_event("NEG", "NEGOTIATION.OPENED")

    assert classification.classification == "ORDER_NEGOTIATION"
    assert classification.requires_order_fetch is True
    assert classification.updates_status is True
