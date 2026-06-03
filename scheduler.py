import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from config.settings import SCHEDULE_MORNING, SCHEDULE_EVENING, SCHEDULE_DRAMA
from jobs import run_morning_job, run_evening_job, run_drama_job

logger = logging.getLogger(__name__)


def start():
    scheduler = BlockingScheduler(timezone="Asia/Ho_Chi_Minh")

    morning_h, morning_m = SCHEDULE_MORNING.split(":")
    evening_h, evening_m = SCHEDULE_EVENING.split(":")
    drama_h, drama_m = SCHEDULE_DRAMA.split(":")

    scheduler.add_job(
        run_morning_job,
        CronTrigger(hour=int(morning_h), minute=int(morning_m)),
        id="morning",
        name="Tổng kết kết quả đêm qua",
    )
    scheduler.add_job(
        run_evening_job,
        CronTrigger(hour=int(evening_h), minute=int(evening_m)),
        id="evening",
        name="Preview trận tối nay",
    )
    scheduler.add_job(
        run_drama_job,
        CronTrigger(hour=int(drama_h), minute=int(drama_m)),
        id="drama",
        name="Bài drama / trending",
    )

    logger.info(
        "Scheduler started — morning=%s, evening=%s, drama=%s (Asia/Ho_Chi_Minh)",
        SCHEDULE_MORNING, SCHEDULE_EVENING, SCHEDULE_DRAMA,
    )
    scheduler.start()
