from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.logging import get_logger
from app.events.polling_service import build_polling_service

settings = get_settings()
logger = get_logger(__name__)
scheduler = AsyncIOScheduler()


async def poll_ifood_events_job() -> None:
    logger.info("Scheduler triggered polling job.")
    service = build_polling_service()
    result = await service.poll_once()
    logger.info("Polling cycle finished.", extra={"polling_result": result.model_dump()})


def start_scheduler() -> None:
    if scheduler.running:
        logger.info("Scheduler start skipped because it is already running.")
        return

    scheduler.add_job(
        poll_ifood_events_job,
        "interval",
        seconds=settings.polling_interval_seconds,
        id="ifood-events-polling",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started.",
        extra={
            "polling_interval_seconds": settings.polling_interval_seconds,
            "scheduler_job_id": "ifood-events-polling",
        },
    )


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
