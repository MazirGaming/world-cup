import logging
import argparse
import sys
from config.settings import LOG_LEVEL
from storage.database import init_db

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("world_cup.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="World Cup Facebook Bot")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "morning", "spotlight", "drama", "factoid", "debate", "evening"],
        help="run: start scheduler | các job khác: chạy thủ công",
    )
    args = parser.parse_args()

    init_db()

    if args.command == "run":
        from scheduler import start
        start()
    else:
        from jobs import (
            run_morning_job, run_spotlight_job, run_drama_job,
            run_factoid_job, run_debate_job, run_evening_job,
        )
        jobs = {
            "morning": run_morning_job,
            "spotlight": run_spotlight_job,
            "drama": run_drama_job,
            "factoid": run_factoid_job,
            "debate": run_debate_job,
            "evening": run_evening_job,
        }
        jobs[args.command]()


if __name__ == "__main__":
    main()
