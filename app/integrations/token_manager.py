from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cached_token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_valid_token(self) -> str:
        if self._should_use_cached_token():
            return self._cached_token  # type: ignore[return-value]

        async with self._lock:
            if self._should_use_cached_token():
                return self._cached_token  # type: ignore[return-value]

            return await self._generate_token()

    async def force_refresh(self) -> str:
        async with self._lock:
            self._cached_token = None
            self._expires_at = None
            return await self._generate_token()

    def _should_use_cached_token(self) -> bool:
        if not self._cached_token or not self._expires_at:
            return False
        return datetime.now(timezone.utc) < self._expires_at

    def _has_client_credentials(self) -> bool:
        return all(
            [
                self.settings.ifood_token_url,
                self.settings.ifood_client_id,
                self.settings.ifood_client_secret,
            ]
        )

    def _has_refresh_fallback(self) -> bool:
        return self._has_client_credentials() and bool(self.settings.ifood_refresh_token)

    async def _generate_token(self) -> str:
        if self._has_client_credentials():
            try:
                return await self._request_client_credentials_token()
            except httpx.HTTPError:
                if self._has_refresh_fallback():
                    logger.warning(
                        "client_credentials token generation failed. Trying refresh_token fallback."
                    )
                    return await self._request_refresh_token()
                raise

        if self.settings.ifood_bearer_token:
            logger.warning(
                "Using fixed iFood bearer token because client_credentials is not configured."
            )
            return self.settings.ifood_bearer_token

        raise RuntimeError(
            "Missing iFood authentication settings. "
            "Provide client_credentials settings or IFOOD_BEARER_TOKEN."
        )

    async def _request_client_credentials_token(self) -> str:
        payload = {
            "grantType": "client_credentials",
            "clientId": self.settings.ifood_client_id,
            "clientSecret": self.settings.ifood_client_secret,
        }

        logger.info(
            "Generating new iFood access token via client_credentials.",
            extra={
                "token_url": self.settings.ifood_token_url,
                "grant_type": "client_credentials",
            },
        )

        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.post(
                self.settings.ifood_token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

        return self._cache_token_from_response(data, grant_type="client_credentials")

    async def _request_refresh_token(self) -> str:
        payload = {
            "grantType": "refresh_token",
            "clientId": self.settings.ifood_client_id,
            "clientSecret": self.settings.ifood_client_secret,
            "refreshToken": self.settings.ifood_refresh_token,
        }

        logger.info(
            "Generating new iFood access token via refresh_token fallback.",
            extra={
                "token_url": self.settings.ifood_token_url,
                "grant_type": "refresh_token",
            },
        )

        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.post(
                self.settings.ifood_token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

        return self._cache_token_from_response(data, grant_type="refresh_token")

    def _cache_token_from_response(self, data: dict, *, grant_type: str) -> str:
        access_token = data.get("accessToken") or data.get("access_token")
        if not access_token:
            raise RuntimeError("iFood token response did not include accessToken/access_token.")

        expires_in = int(data.get("expiresIn") or data.get("expires_in") or 3600)
        refresh_deadline = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 300, 60))

        self._cached_token = access_token
        self._expires_at = refresh_deadline

        logger.info(
            "iFood access token generated and cached.",
            extra={
                "grant_type": grant_type,
                "expires_in_seconds": expires_in,
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
                "refresh_before_at": refresh_deadline.isoformat(),
            },
        )
        return access_token


@lru_cache(maxsize=1)
def get_token_manager() -> TokenManager:
    return TokenManager(get_settings())
