from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import get_settings
from db.database import get_session_factory
from services.product_service import ProductService

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_price_check():
    """Scheduled job: check all active products."""
    logger.info("Scheduled price check starting...")
    factory = get_session_factory()
    session = factory()
    try:
        service = ProductService(session)
        results = service.check_all_active()
        total_deals = sum(r.get("deals_found", 0) for r in results)
        logger.info(f"Scheduled check complete: {len(results)} products, {total_deals} deals found")
    except Exception as e:
        logger.error(f"Scheduled price check failed: {e}")
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    settings = get_settings().monitoring

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_price_check,
        trigger=IntervalTrigger(minutes=settings.check_interval_minutes),
        id="price_check",
        name="Periodic Price Check",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"Scheduler started: checking every {settings.check_interval_minutes} minutes")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
