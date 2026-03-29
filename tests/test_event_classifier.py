from app.events.event_classifier import classify_event, extract_event_key


def test_extract_event_key_from_full_code() -> None:
    assert extract_event_key("RTP", "ORDER_STATUS.READY_TO_PICKUP") == "READY_TO_PICKUP"


def test_classify_placed_event_enables_fetch_and_confirm() -> None:
    classification = classify_event("PLC", "ORDER_STATUS.PLACED")

    assert classification.classification == "ORDER_PLACED"
    assert classification.requires_order_fetch is True
    assert classification.auto_action == "confirm"
