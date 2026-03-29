"""initial schema

Revision ID: 20260328_000001
Revises:
Create Date: 2026-03-28 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260328_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_polling_runs",
        sa.Column("run_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_event_count", sa.Integer(), nullable=False),
        sa.Column("new_event_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_event_count", sa.Integer(), nullable=False),
        sa.Column("ack_attempted", sa.Boolean(), nullable=False),
        sa.Column("ack_success", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_uuid", name="uq_event_polling_runs_run_uuid"),
    )

    op.create_table(
        "merchants",
        sa.Column("ifood_merchant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ifood_merchant_id", name="uq_merchants_ifood_merchant_id"),
    )

    op.create_table(
        "orders",
        sa.Column("merchant_id", sa.BigInteger(), nullable=False),
        sa.Column("ifood_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_id", sa.String(length=50), nullable=True),
        sa.Column("sales_channel", sa.String(length=50), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("order_type", sa.String(length=30), nullable=True),
        sa.Column("order_timing", sa.String(length=30), nullable=True),
        sa.Column("current_status", sa.String(length=100), nullable=False),
        sa.Column("external_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preparation_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_to_pickup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_source", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("delivery_fee_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("benefits_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("additional_fees_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("payments_pending", sa.Boolean(), nullable=True),
        sa.Column("payments_prepaid", sa.Boolean(), nullable=True),
        sa.Column("customer_notes", sa.Text(), nullable=True),
        sa.Column("latest_event_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ifood_order_id", name="uq_orders_ifood_order_id"),
    )

    op.create_table(
        "order_event_receipts",
        sa.Column("polling_run_id", sa.BigInteger(), nullable=False),
        sa.Column("merchant_id", sa.BigInteger(), nullable=False),
        sa.Column("receipt_index", sa.Integer(), nullable=False),
        sa.Column("ifood_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ifood_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_code", sa.String(length=10), nullable=False),
        sa.Column("event_full_code", sa.String(length=100), nullable=False),
        sa.Column("event_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sales_channel", sa.String(length=50), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["polling_run_id"], ["event_polling_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("polling_run_id", "receipt_index", name="uq_order_event_receipts_run_receipt_index"),
    )

    op.create_table(
        "order_events_raw",
        sa.Column("merchant_id", sa.BigInteger(), nullable=False),
        sa.Column("ifood_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ifood_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_code", sa.String(length=10), nullable=False),
        sa.Column("event_full_code", sa.String(length=100), nullable=False),
        sa.Column("event_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sales_channel", sa.String(length=50), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("first_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receive_count", sa.Integer(), nullable=False),
        sa.Column("first_polling_run_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["first_polling_run_id"], ["event_polling_runs.id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ifood_event_id", name="uq_order_events_raw_ifood_event_id"),
    )

    op.create_table(
        "order_event_acknowledgment_batches",
        sa.Column("polling_run_id", sa.BigInteger(), nullable=False),
        sa.Column("requested_event_count", sa.Integer(), nullable=False),
        sa.Column("acknowledged_event_count", sa.Integer(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("request_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["polling_run_id"], ["event_polling_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "event_processing_state",
        sa.Column("order_event_id", sa.BigInteger(), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("classified_as", sa.String(length=50), nullable=False),
        sa.Column("requires_order_fetch", sa.Boolean(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=50), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_owner", sa.String(length=100), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_event_id"], ["order_events_raw.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_event_id", name="uq_event_processing_state_order_event_id"),
    )

    op.create_table(
        "order_event_acknowledgment_items",
        sa.Column("ack_batch_id", sa.BigInteger(), nullable=False),
        sa.Column("order_event_id", sa.BigInteger(), nullable=True),
        sa.Column("ifood_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_result_status", sa.String(length=20), nullable=False),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ack_batch_id"], ["order_event_acknowledgment_batches.id"]),
        sa.ForeignKeyConstraint(["order_event_id"], ["order_events_raw.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ack_batch_id", "ifood_event_id", name="uq_order_event_ack_items_batch_event"),
    )

    op.create_table(
        "order_customers",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("ifood_customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("document_number", sa.String(length=50), nullable=True),
        sa.Column("phone_number", sa.String(length=50), nullable=True),
        sa.Column("phone_localizer", sa.String(length=20), nullable=True),
        sa.Column("phone_localizer_expiration", sa.String(length=50), nullable=True),
        sa.Column("orders_count_on_merchant", sa.Integer(), nullable=True),
        sa.Column("segmentation", sa.String(length=100), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_order_customers_order_id"),
    )

    op.create_table(
        "order_deliveries",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("delivery_mode", sa.String(length=30), nullable=False),
        sa.Column("delivered_by", sa.String(length=30), nullable=True),
        sa.Column("address_street", sa.String(length=255), nullable=True),
        sa.Column("address_number", sa.String(length=50), nullable=True),
        sa.Column("address_complement", sa.String(length=255), nullable=True),
        sa.Column("address_neighborhood", sa.String(length=255), nullable=True),
        sa.Column("address_city", sa.String(length=255), nullable=True),
        sa.Column("address_state", sa.String(length=100), nullable=True),
        sa.Column("address_country", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("pickup_code", sa.String(length=100), nullable=True),
        sa.Column("delivery_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("takeout_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schedule_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schedule_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_order_deliveries_order_id"),
    )

    op.create_table(
        "order_items",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("item_sequence", sa.Integer(), nullable=False),
        sa.Column("ifood_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unique_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("integration_id", sa.String(length=100), nullable=True),
        sa.Column("external_code", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("item_type", sa.String(length=50), nullable=True),
        sa.Column("display_index", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("ean", sa.String(length=50), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("unit_price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("options_price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total_price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "item_sequence", name="uq_order_items_order_sequence"),
    )

    op.create_table(
        "order_payments",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("payment_sequence", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=100), nullable=False),
        sa.Column("payment_type", sa.String(length=50), nullable=True),
        sa.Column("prepaid", sa.Boolean(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("change_for_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("card_brand", sa.String(length=50), nullable=True),
        sa.Column("authorization_code", sa.String(length=100), nullable=True),
        sa.Column("acquirer_document", sa.String(length=100), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "payment_sequence", name="uq_order_payments_order_sequence"),
    )

    op.create_table(
        "order_benefits",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("benefit_sequence", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("benefit_type", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("campaign_id", sa.String(length=100), nullable=True),
        sa.Column("campaign_name", sa.String(length=255), nullable=True),
        sa.Column("sponsorship_values_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "benefit_sequence", name="uq_order_benefits_order_sequence"),
    )

    op.create_table(
        "order_snapshots",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("source_event_id", sa.BigInteger(), nullable=True),
        sa.Column("snapshot_type", sa.String(length=20), nullable=False),
        sa.Column("fetch_source", sa.String(length=20), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["source_event_id"], ["order_events_raw.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "order_status_history",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("source_event_id", sa.BigInteger(), nullable=True),
        sa.Column("status_code", sa.String(length=10), nullable=True),
        sa.Column("status_full_code", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["source_event_id"], ["order_events_raw.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_event_id", name="uq_order_status_history_source_event_id"),
    )

    op.create_table(
        "action_requests",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("merchant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_event_id", sa.BigInteger(), nullable=True),
        sa.Column("confirmed_by_event_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("trigger_mode", sa.String(length=20), nullable=False),
        sa.Column("active_mode", sa.Boolean(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("request_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_status", sa.String(length=30), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("external_confirmation_expected", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["confirmed_by_event_id"], ["order_events_raw.id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["source_event_id"], ["order_events_raw.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "action_type", "source_event_id", name="uq_action_requests_order_action_event"),
    )

    op.create_table(
        "integration_logs",
        sa.Column("merchant_id", sa.BigInteger(), nullable=True),
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        sa.Column("order_event_id", sa.BigInteger(), nullable=True),
        sa.Column("polling_run_id", sa.BigInteger(), nullable=True),
        sa.Column("action_request_id", sa.BigInteger(), nullable=True),
        sa.Column("integration_name", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("http_method", sa.String(length=10), nullable=False),
        sa.Column("url_path", sa.String(length=255), nullable=False),
        sa.Column("request_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("error_type", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["action_request_id"], ["action_requests.id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["order_event_id"], ["order_events_raw.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["polling_run_id"], ["event_polling_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "order_item_options",
        sa.Column("order_item_id", sa.BigInteger(), nullable=False),
        sa.Column("option_sequence", sa.Integer(), nullable=False),
        sa.Column("ifood_option_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unique_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("integration_id", sa.String(length=100), nullable=True),
        sa.Column("group_name", sa.String(length=255), nullable=True),
        sa.Column("option_type", sa.String(length=50), nullable=True),
        sa.Column("addition", sa.Boolean(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("unit_price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total_price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("customization_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", "option_sequence", name="uq_order_item_options_item_sequence"),
    )


def downgrade() -> None:
    op.drop_table("order_item_options")
    op.drop_table("integration_logs")
    op.drop_table("action_requests")
    op.drop_table("order_status_history")
    op.drop_table("order_snapshots")
    op.drop_table("order_benefits")
    op.drop_table("order_payments")
    op.drop_table("order_items")
    op.drop_table("order_deliveries")
    op.drop_table("order_customers")
    op.drop_table("order_event_acknowledgment_items")
    op.drop_table("event_processing_state")
    op.drop_table("order_event_acknowledgment_batches")
    op.drop_table("order_events_raw")
    op.drop_table("order_event_receipts")
    op.drop_table("orders")
    op.drop_table("merchants")
    op.drop_table("event_polling_runs")
