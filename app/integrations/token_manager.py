from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings


class TokenManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cached_token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_valid_token(self) -> str:
        if self.settings.ifood_bearer_token:
            return self.settings.ifood_bearer_token

        if self._cached_token and self._expires_at and datetime.now(timezone.utc) < self._expires_at:
            return self._cached_token

        async with self._lock:
            if self._cached_token and self._expires_at and datetime.now(timezone.utc) < self._expires_at:
                return self._cached_token

            return await self._refresh_access_token()

    async def _refresh_access_token(self) -> str:
        if not all(
            [
                self.settings.ifood_token_url,
                self.settings.ifood_client_id,
                self.settings.ifood_client_secret,
                self.settings.ifood_refresh_token,
            ]
        ):
            raise RuntimeError(
                "Missing iFood authentication settings. "
                "Provide IFOOD_BEARER_TOKEN or the OAuth refresh credentials."
            )

        payload = {
            "grantType": "refresh_token",
            "clientId": self.settings.ifood_client_id,
            "clientSecret": self.settings.ifood_client_secret,
            "refreshToken": self.settings.ifood_refresh_token,
        }

        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.post(self.settings.ifood_token_url, json=payload)
            response.raise_for_status()
            data = response.json()

        access_token = data.get("accessToken") or data.get("access_token")
        if not access_token:
            raise RuntimeError("iFood token response did not include accessToken/access_token.")

        expires_in = int(data.get("expiresIn") or data.get("expires_in") or 3600)
        self._cached_token = access_token
        self._expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 60, 60))
        return access_token


@lru_cache(maxsize=1)
def get_token_manager() -> TokenManager:
    return TokenManager(get_settings())
