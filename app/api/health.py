from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck() -> dict:
    settings = get_settings()
    db_status = "up"

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive
        db_status = f"down: {exc}"

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "db": db_status,
        "scheduler_enabled": settings.scheduler_enabled,
        "orders_active_mode": settings.orders_active_mode,
        "enabled_automatic_actions": sorted(settings.enabled_automatic_actions),
    }
