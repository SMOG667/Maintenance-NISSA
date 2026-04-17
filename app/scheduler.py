"""Planificateur de taches automatiques."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import DAILY_CHECK_TIME, TIMEZONE
from app.database import SessionLocal
from app.session import start_daily_check

logger = logging.getLogger("nissa.scheduler")

scheduler = BackgroundScheduler(timezone=TIMEZONE)


def daily_check_job():
    """Job cron : envoi du check journalier."""
    logger.info("Execution du job cron journalier")
    db = SessionLocal()
    try:
        start_daily_check(db)
    finally:
        db.close()


def start_scheduler():
    """Demarre le planificateur."""
    hour, minute = DAILY_CHECK_TIME.split(":")

    scheduler.add_job(
        daily_check_job,
        CronTrigger(hour=int(hour), minute=int(minute), timezone=TIMEZONE),
        id="daily_check",
        name="Check journalier Nissa",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler demarre - check journalier a {DAILY_CHECK_TIME} ({TIMEZONE})")


def stop_scheduler():
    """Arrete le planificateur."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler arrete")
