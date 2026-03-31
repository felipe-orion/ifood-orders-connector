from __future__ import annotations

import argparse
import time

import httpx


def _call_action(base_url: str, order_id: str, action_path: str) -> None:
    url = f"{base_url}/internal/orders/{order_id}/{action_path}"
    response = httpx.post(url, timeout=30.0)
    print(f"\n[{action_path}] {response.status_code}")
    try:
        print(response.json())
    except ValueError:
        print(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a manual iFood homologation order flow.")
    parser.add_argument("order_id", help="Local iFood order UUID already persisted in the connector")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay in seconds between actions")
    args = parser.parse_args()

    print(f"Running homologation flow for order {args.order_id}")
    print(f"Base URL: {args.base_url}")
    print(f"Delay between actions: {args.delay}s")

    _call_action(args.base_url, args.order_id, "confirm")
    time.sleep(args.delay)
    _call_action(args.base_url, args.order_id, "start-preparation")
    time.sleep(args.delay)
    _call_action(args.base_url, args.order_id, "ready")
    time.sleep(args.delay)
    _call_action(args.base_url, args.order_id, "dispatch")

    status_response = httpx.get(f"{args.base_url}/internal/orders/{args.order_id}/status", timeout=30.0)
    print("\n[status]")
    print(status_response.status_code)
    try:
        print(status_response.json())
    except ValueError:
        print(status_response.text)


if __name__ == "__main__":
    main()
