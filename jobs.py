import logging
from collectors.football_api import get_yesterday_matches, get_today_matches
from collectors.news_feed import fetch_all_news
from generator.content import (
    generate_morning_post,
    generate_evening_post,
    generate_drama_post,
    generate_buildup_post,
    generate_image,
)
from publisher.facebook import publish_post
from storage.database import get_unused_news, mark_news_used, save_post, mark_post_published

logger = logging.getLogger(__name__)


def _had_real_matches(matches: list[dict]) -> bool:
    return any(m["status"] == "FINISHED" for m in matches)


def _has_matches_tonight(matches: list[dict]) -> bool:
    return any(m["status"] in ("SCHEDULED", "TIMED") for m in matches)


def run_morning_job():
    logger.info("=== Morning job started ===")
    try:
        matches = get_yesterday_matches()
        fetch_all_news()
        news = get_unused_news(limit=6)

        if _had_real_matches(matches):
            content = generate_morning_post(matches, news)
            post_type = "morning"
        else:
            logger.info("No finished matches yesterday — switching to buildup post")
            if not news:
                logger.warning("No news available, skipping morning post")
                return
            content = generate_buildup_post(news)
            post_type = "buildup"

        if not content:
            logger.warning("No content generated for morning post")
            return

        image_url = generate_image(post_type)
        post_id = save_post(post_type, content)
        fb_id = publish_post(content, image_url)
        if fb_id:
            mark_post_published(post_id, fb_id)
            mark_news_used([n.id for n in news])
        logger.info("=== Morning job done ===")
    except Exception:
        logger.exception("Morning job failed")


def run_evening_job():
    logger.info("=== Evening job started ===")
    try:
        matches = get_today_matches()
        fetch_all_news()
        news = get_unused_news(limit=4)

        if _has_matches_tonight(matches):
            content = generate_evening_post(matches, news)
            post_type = "evening"
        else:
            logger.info("No matches tonight — switching to buildup post")
            if not news:
                logger.warning("No news available, skipping evening post")
                return
            content = generate_buildup_post(news)
            post_type = "buildup"

        if not content:
            logger.warning("No content generated for evening post")
            return

        image_url = generate_image(post_type)
        post_id = save_post(post_type, content)
        fb_id = publish_post(content, image_url)
        if fb_id:
            mark_post_published(post_id, fb_id)
            mark_news_used([n.id for n in news])
        logger.info("=== Evening job done ===")
    except Exception:
        logger.exception("Evening job failed")


def run_drama_job():
    logger.info("=== Drama job started ===")
    try:
        fetch_all_news()
        news = get_unused_news(limit=8)

        if not news:
            logger.warning("No news available, skipping drama post")
            return

        content = generate_drama_post(news)
        if not content:
            logger.warning("No drama content generated")
            return

        image_url = generate_image("drama")
        post_id = save_post("drama", content)
        fb_id = publish_post(content, image_url)
        if fb_id:
            mark_post_published(post_id, fb_id)
            mark_news_used([n.id for n in news])
        logger.info("=== Drama job done ===")
    except Exception:
        logger.exception("Drama job failed")
