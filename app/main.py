from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.health import router as health_router
from app.api.internal import router as internal_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger
from app.tasks.scheduler import shutdown_scheduler, start_scheduler
from app.web.panel import router as panel_router

configure_logging()
settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
)

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")
app.include_router(health_router)
app.include_router(internal_router, prefix="/internal", tags=["internal"])
app.include_router(panel_router, tags=["panel"])


@app.on_event("startup")
def on_startup() -> None:
    if settings.db_auto_create:
        logger.info("Creating database schema from models because DB_AUTO_CREATE is enabled.")
        init_db()

    if settings.scheduler_enabled:
        start_scheduler()

    logger.info(
        "Application started.",
        extra={
            "orders_active_mode": settings.orders_active_mode,
            "enabled_automatic_actions": sorted(settings.enabled_automatic_actions),
            "scheduler_enabled": settings.scheduler_enabled,
        },
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    shutdown_scheduler()
    logger.info("Application stopped.")
