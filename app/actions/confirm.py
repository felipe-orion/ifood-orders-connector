from __future__ import annotations

from app.integrations.ifood_client import IfoodClient


class ConfirmAction:
    def __init__(self, ifood_client: IfoodClient) -> None:
        self.ifood_client = ifood_client

    async def execute(self, order_id: str):
        return await self.ifood_client.confirm_order(order_id)
