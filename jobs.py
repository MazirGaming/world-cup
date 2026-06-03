import logging
from collectors.football_api import get_yesterday_matches, get_today_matches
from collectors.news_feed import fetch_all_news
from generator.content import generate_morning_post, generate_evening_post, generate_drama_post, generate_image
from publisher.facebook import publish_post
from storage.database import get_unused_news, mark_news_used, save_post, mark_post_published

logger = logging.getLogger(__name__)


def run_morning_job():
    logger.info("=== Morning job started ===")
    try:
        matches = get_yesterday_matches()
        fetch_all_news()
        news = get_unused_news(limit=6)

        content = generate_morning_post(matches, news)
        if not content:
            logger.warning("No content generated for morning post")
            return

        image_url = generate_image("morning")
        post_id = save_post("morning", content)
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

        content = generate_evening_post(matches, news)
        if not content:
            logger.warning("No matches tonight, skipping evening post")
            return

        image_url = generate_image("evening")
        post_id = save_post("evening", content)
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
