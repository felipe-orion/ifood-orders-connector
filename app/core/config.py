import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def _env_list(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "Orders Connector")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = _env_bool("DEBUG", True)

        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/orders_connector",
        )
        self.db_echo = _env_bool("DB_ECHO", False)
        self.db_auto_create = _env_bool("DB_AUTO_CREATE", False)

        self.scheduler_enabled = _env_bool("SCHEDULER_ENABLED", True)
        self.polling_interval_seconds = _env_int("POLLING_INTERVAL_SECONDS", 30)
        self.polling_retry_attempts = _env_int("POLLING_RETRY_ATTEMPTS", 3)
        self.polling_retry_base_delay_seconds = _env_float("POLLING_RETRY_BASE_DELAY_SECONDS", 1.0)
        self.orders_read_retry_attempts = _env_int("ORDERS_READ_RETRY_ATTEMPTS", 3)
        self.orders_read_retry_base_delay_seconds = _env_float("ORDERS_READ_RETRY_BASE_DELAY_SECONDS", 1.0)
        self.orders_active_mode = _env_bool("ORDERS_ACTIVE_MODE", False)
        self.enabled_automatic_actions = {item.lower() for item in _env_list("ENABLED_AUTOMATIC_ACTIONS")} or {
            "confirm"
        }

        self.http_timeout_seconds = _env_float("HTTP_TIMEOUT_SECONDS", 15.0)

        self.ifood_events_base_url = os.getenv(
            "IFOOD_EVENTS_BASE_URL",
            "https://merchant-api.ifood.com.br/events/v1.0",
        ).rstrip("/")
        self.ifood_orders_base_url = os.getenv(
            "IFOOD_ORDERS_BASE_URL",
            "https://merchant-api.ifood.com.br/order/v1.0",
        ).rstrip("/")
        self.ifood_token_url = os.getenv("IFOOD_TOKEN_URL", "").strip()
        self.ifood_client_id = os.getenv("IFOOD_CLIENT_ID", "").strip()
        self.ifood_client_secret = os.getenv("IFOOD_CLIENT_SECRET", "").strip()
        self.ifood_refresh_token = os.getenv("IFOOD_REFRESH_TOKEN", "").strip()
        self.ifood_bearer_token = os.getenv("IFOOD_BEARER_TOKEN", "").strip()
        self.ifood_polling_merchants = _env_list("IFOOD_POLLING_MERCHANTS")

        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
