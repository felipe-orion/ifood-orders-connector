from __future__ import annotations

from collections.abc import Iterable


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _safe_datetime_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("value", "start", "end", "dateTime"):
            candidate = _safe_str(value.get(key))
            if candidate:
                return candidate
        return None
    return _safe_str(value)


def _safe_amount(value) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, dict):
        candidate = value.get("value")
        if candidate is None:
            candidate = value.get("amount")
        return _safe_amount(candidate)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        normalized = stripped.replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None

    return None


def _safe_currency(value, default: str = "BRL") -> str:
    if isinstance(value, dict):
        currency = _safe_str(value.get("currency"))
        if currency:
            return currency.upper()

    if isinstance(value, str):
        stripped = value.strip()
        if len(stripped) == 3 and stripped.isalpha():
            return stripped.upper()

    return default


def _safe_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _normalize_header(raw_order: dict) -> dict:
    total = _safe_dict(raw_order.get("total"))
    payments = _safe_dict(raw_order.get("payments"))
    cancellation = _safe_dict(raw_order.get("cancellation"))

    currency = (
        _safe_currency(total.get("orderAmount"), default="")
        or _safe_currency(total.get("subTotal"), default="")
        or _safe_currency(total.get("deliveryFee"), default="")
        or _safe_currency(total.get("benefits"), default="")
        or "BRL"
    )

    return {
        "ifood_order_id": _safe_str(raw_order.get("id")),
        "display_id": _safe_str(raw_order.get("displayId")),
        "sales_channel": _safe_str(raw_order.get("salesChannel")),
        "category": _safe_str(raw_order.get("category")),
        "order_type": _safe_str(raw_order.get("orderType")),
        "order_timing": _safe_str(raw_order.get("orderTiming")),
        "current_status": _safe_str(raw_order.get("orderStatus") or raw_order.get("status")) or "PLACED",
        "external_created_at": _safe_datetime_str(raw_order.get("createdAt")),
        "preparation_start_at": _safe_datetime_str(raw_order.get("preparationStartDateTime")),
        "currency": currency,
        "subtotal_amount": _safe_amount(total.get("subTotal")),
        "delivery_fee_amount": _safe_amount(total.get("deliveryFee")),
        "benefits_amount": _safe_amount(total.get("benefits")),
        "additional_fees_amount": _safe_amount(total.get("additionalFees")),
        "total_amount": _safe_amount(total.get("orderAmount")),
        "payments_pending": _safe_bool(payments.get("pending")),
        "payments_prepaid": _safe_bool(payments.get("prepaid")),
        "customer_notes": _safe_str(raw_order.get("additionalInfo") or raw_order.get("additionalInstructions")),
        "cancellation_source": _safe_str(cancellation.get("source")),
    }


def _normalize_customer(raw_order: dict) -> dict:
    customer = _safe_dict(raw_order.get("customer"))
    phone = _safe_dict(customer.get("phone"))

    return {
        "ifood_customer_id": _safe_str(customer.get("id")),
        "name": _safe_str(customer.get("name")),
        "document_number": _safe_str(customer.get("documentNumber")),
        "phone_number": _safe_str(phone.get("number")),
        "phone_localizer": _safe_str(phone.get("localizer")),
        "phone_localizer_expiration": _safe_str(phone.get("localizerExpiration")),
        "orders_count_on_merchant": customer.get("ordersCountOnMerchant"),
        "segmentation": _safe_str(customer.get("segmentation")),
    }


def _normalize_delivery(raw_order: dict) -> dict:
    delivery = _safe_dict(raw_order.get("delivery"))
    takeout = _safe_dict(raw_order.get("takeout"))
    schedule = _safe_dict(raw_order.get("schedule"))
    address = _safe_dict(delivery.get("deliveryAddress") or delivery.get("address"))
    coordinates = _safe_dict(address.get("coordinates"))

    return {
        "delivery_mode": "DELIVERY" if delivery else "TAKEOUT",
        "delivered_by": _safe_str(delivery.get("deliveredBy")),
        "address_street": _safe_str(address.get("streetName")),
        "address_number": _safe_str(address.get("streetNumber")),
        "address_complement": _safe_str(address.get("complement")),
        "address_neighborhood": _safe_str(address.get("neighborhood")),
        "address_city": _safe_str(address.get("city")),
        "address_state": _safe_str(address.get("state")),
        "address_country": _safe_str(address.get("country")),
        "postal_code": _safe_str(address.get("postalCode")),
        "latitude": _safe_amount(coordinates.get("latitude")),
        "longitude": _safe_amount(coordinates.get("longitude")),
        "pickup_code": _safe_str(delivery.get("pickupCode") or takeout.get("pickupCode")),
        "delivery_datetime": _safe_datetime_str(delivery.get("deliveryDateTime")),
        "takeout_datetime": _safe_datetime_str(takeout.get("takeoutDateTime")),
        "schedule_start_at": _safe_datetime_str(schedule.get("deliveryDateTimeStart")),
        "schedule_end_at": _safe_datetime_str(schedule.get("deliveryDateTimeEnd")),
    }


def _normalize_options(options: Iterable[dict] | None) -> list[dict]:
    normalized_options: list[dict] = []
    for option_index, option_value in enumerate(_safe_list(options), start=1):
        option = _safe_dict(option_value)
        normalized_options.append(
            {
                "option_sequence": option_index,
                "ifood_option_id": _safe_str(option.get("id")),
                "unique_id": _safe_str(option.get("uniqueId")),
                "integration_id": _safe_str(option.get("integrationId")),
                "group_name": _safe_str(option.get("groupName")),
                "option_type": _safe_str(option.get("type")),
                "addition": _safe_bool(option.get("addition")),
                "name": _safe_str(option.get("name")),
                "quantity": _safe_amount(option.get("quantity")) or 1.0,
                "unit_price_amount": _safe_amount(option.get("unitPrice")),
                "total_price_amount": _safe_amount(option.get("price")) or _safe_amount(option.get("totalPrice")),
                "customization_json": option.get("customization"),
            }
        )
    return normalized_options


def _normalize_items(raw_order: dict) -> list[dict]:
    normalized_items: list[dict] = []
    for item_index, item_value in enumerate(_safe_list(raw_order.get("items")), start=1):
        item = _safe_dict(item_value)
        normalized_items.append(
            {
                "item_sequence": item_index,
                "ifood_item_id": _safe_str(item.get("id")),
                "unique_id": _safe_str(item.get("uniqueId")),
                "integration_id": _safe_str(item.get("integrationId")),
                "external_code": _safe_str(item.get("externalCode")),
                "name": _safe_str(item.get("name")),
                "item_type": _safe_str(item.get("type") or item.get("productType")),
                "display_index": item.get("index"),
                "quantity": _safe_amount(item.get("quantity")) or 1.0,
                "unit": _safe_str(item.get("unit")),
                "ean": _safe_str(item.get("ean")),
                "image_url": _safe_str(item.get("imageUrl")),
                "unit_price_amount": _safe_amount(item.get("unitPrice")),
                "options_price_amount": _safe_amount(item.get("optionsPrice")),
                "total_price_amount": _safe_amount(item.get("totalPrice")) or _safe_amount(item.get("price")),
                "observations": _safe_str(item.get("observations")),
                "options": _normalize_options(item.get("options")),
            }
        )
    return normalized_items


def _normalize_payments(raw_order: dict) -> list[dict]:
    payments = _safe_dict(raw_order.get("payments"))
    methods = _safe_list(payments.get("methods"))

    normalized_methods: list[dict] = []
    for index, payment_value in enumerate(methods, start=1):
        payment = _safe_dict(payment_value)
        cash = _safe_dict(payment.get("cash"))
        card = _safe_dict(payment.get("card"))
        transaction = _safe_dict(payment.get("transaction"))
        value = payment.get("value")

        normalized_methods.append(
            {
                "payment_sequence": index,
                "method": _safe_str(payment.get("method")) or "UNKNOWN",
                "payment_type": _safe_str(payment.get("type")),
                "prepaid": _safe_bool(payment.get("prepaid")) if payment.get("prepaid") is not None else _safe_bool(payments.get("prepaid")),
                "currency": _safe_currency(value, default="BRL"),
                "amount": _safe_amount(value) or 0.0,
                "change_for_amount": _safe_amount(cash.get("changeFor")),
                "card_brand": _safe_str(card.get("brand")),
                "authorization_code": _safe_str(transaction.get("authorizationCode")),
                "acquirer_document": _safe_str(transaction.get("acquirerDocument")),
            }
        )

    return normalized_methods


def _normalize_benefits(raw_order: dict) -> list[dict]:
    normalized_benefits: list[dict] = []
    for index, benefit_value in enumerate(_safe_list(raw_order.get("benefits")), start=1):
        benefit = _safe_dict(benefit_value)
        campaign = _safe_dict(benefit.get("campaign"))
        normalized_benefits.append(
            {
                "benefit_sequence": index,
                "target_id": _safe_str(benefit.get("targetId")),
                "benefit_type": _safe_str(benefit.get("target") or benefit.get("type")),
                "description": _safe_str(benefit.get("description")),
                "campaign_id": _safe_str(campaign.get("id")),
                "campaign_name": _safe_str(campaign.get("name")),
                "sponsorship_values_json": benefit.get("sponsorshipValues"),
                "amount": _safe_amount(benefit.get("value")) or 0.0,
            }
        )
    return normalized_benefits


def normalize_order(raw_order: dict) -> dict:
    safe_order = _safe_dict(raw_order)
    return {
        "header": _normalize_header(safe_order),
        "customer": _normalize_customer(safe_order),
        "delivery": _normalize_delivery(safe_order),
        "items": _normalize_items(safe_order),
        "payments": _normalize_payments(safe_order),
        "benefits": _normalize_benefits(safe_order),
    }
