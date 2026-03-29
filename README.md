# Orders Connector

Monolith connector in `FastAPI` for the official iFood Orders flow:

`Events -> persist raw -> ACK -> Orders -> persist normalized -> Actions`

## Requirements

- Python 3.12+
- PostgreSQL 14+

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the example file:

```bash
cp .env.example .env
```

4. Adjust `.env`:

- `DATABASE_URL`
- `IFOOD_BEARER_TOKEN` for quick tests
- or `IFOOD_TOKEN_URL`, `IFOOD_CLIENT_ID`, `IFOOD_CLIENT_SECRET`, `IFOOD_REFRESH_TOKEN`
- `ORDERS_ACTIVE_MODE=false` for a safe initial run
- `ENABLED_AUTOMATIC_ACTIONS=confirm` to control which automations are allowed in active mode

## Database

Option 1, quick bootstrap in development:

```bash
set DB_AUTO_CREATE=true
```

Option 2, with Alembic:

```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

## Run the API

```bash
uvicorn app.main:app --reload
```

## Main endpoints

- `GET /health`
- `GET /internal/config`
- `POST /internal/polling/run-once`
- `GET /internal/orders/{order_id}`
- `POST /internal/actions/{order_id}/confirm`
- `POST /internal/actions/{order_id}/start-preparation`
- `POST /internal/actions/{order_id}/ready-to-pickup`
- `POST /internal/actions/{order_id}/dispatch`
- `GET /internal/actions/{order_id}/cancellation-reasons`
- `POST /internal/actions/{order_id}/request-cancellation`

## Local testing

### 1. Passive mode

Use:

- `ORDERS_ACTIVE_MODE=false`
- `ENABLED_AUTOMATIC_ACTIONS=confirm`

In this mode the app:

- polls events
- persists raw events
- sends ACK
- fetches and persists orders
- does not execute automatic actions

### 2. Run polling manually

```bash
curl -X POST http://127.0.0.1:8000/internal/polling/run-once
```

### 3. Read a locally persisted order

```bash
curl http://127.0.0.1:8000/internal/orders/{ifood_order_id}
```

### 4. Test actions manually

```bash
curl -X POST http://127.0.0.1:8000/internal/actions/{ifood_order_id}/confirm
curl -X POST http://127.0.0.1:8000/internal/actions/{ifood_order_id}/start-preparation
curl -X POST http://127.0.0.1:8000/internal/actions/{ifood_order_id}/ready-to-pickup
curl -X POST http://127.0.0.1:8000/internal/actions/{ifood_order_id}/dispatch
curl http://127.0.0.1:8000/internal/actions/{ifood_order_id}/cancellation-reasons
curl -X POST http://127.0.0.1:8000/internal/actions/{ifood_order_id}/request-cancellation -H "Content-Type: application/json" -d "{\"reason\":\"CUSTOMER_REQUEST\"}"
```

## Tests

Run the basic tests:

```bash
pytest
```

## Observability

Console logs include operational context for:

- polling run
- ACK
- processed event
- order fetch
- executed action
- skipped action
- HTTP failures and unexpected failures

## Operational safety

- Start with `ORDERS_ACTIVE_MODE=false`
- Enable automations only after validating the full flow
- The real order state still comes from events, not from `202`
