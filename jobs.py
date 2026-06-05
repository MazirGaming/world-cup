import logging
import random
from typing import Optional
import httpx
from collectors.football_api import get_yesterday_matches, get_today_matches
from collectors.news_feed import fetch_all_news, fetch_article_image, fetch_article_content
from generator.content import (
    generate_morning_post,
    generate_evening_post,
    generate_drama_post,
    generate_buildup_post,
    generate_spotlight_post,
    generate_factoid_post,
    generate_debate_post,
    generate_image,
    STAR_PLAYERS,
)
from publisher.facebook import publish_post
from publisher.threads import publish_to_threads
from storage.database import get_unused_news, mark_news_used, save_post, mark_post_published

logger = logging.getLogger(__name__)


def _had_real_matches(matches: list[dict]) -> bool:
    return any(m["status"] == "FINISHED" for m in matches)


def _has_matches_tonight(matches: list[dict]) -> bool:
    return any(m["status"] in ("SCHEDULED", "TIMED") for m in matches)


def _get_article_image(news: list) -> Optional[str]:
    """Lấy og:image từ bài báo, validate trước khi dùng."""
    for item in news[:3]:
        img = fetch_article_image(item.url)
        if img and _is_valid_image_url(img):
            logger.info("Using article image from %s", item.url)
            return img
    return None


def _is_valid_image_url(url: str) -> bool:
    # Facebook/Threads reject CDN processing URLs with complex params
    if len(url) > 300:
        return False
    blocked = ["base64", "overlay", "precrop", "enable=upscale", "watermark"]
    if any(p in url for p in blocked):
        return False
    try:
        resp = httpx.head(url, timeout=6, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; WorldCupBot/1.0)"
        })
        return resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/")
    except Exception:
        return False


def _enrich_news_with_body(news: list) -> str:
    """Fetch body của bài báo đầu tiên để AI có nội dung thực tế hơn."""
    if not news:
        return ""
    body = fetch_article_content(news[0].url)
    if body:
        source = news[0].source or ""
        return f"\n\nNỘI DUNG BÀI BÁO [{source}]:\n{body[:1000]}"
    return ""


def _publish(post_type: str, content: str, image_url: str, news: list) -> None:
    if not content:
        logger.warning("No content for %s, skipping", post_type)
        return
    post_id = save_post(post_type, content)
    fb_id = publish_post(content, image_url)
    if fb_id:
        mark_post_published(post_id, fb_id)
        if news:
            mark_news_used([n.id for n in news])
    publish_to_threads(content, image_url)


def run_morning_job():
    logger.info("=== Morning job started ===")
    try:
        matches = get_yesterday_matches()
        fetch_all_news()
        news = get_unused_news(limit=6)

        if _had_real_matches(matches):
            extra = _enrich_news_with_body(news)
            content = generate_morning_post(matches, news, extra_context=extra)
            post_type = "morning"
        else:
            if not news:
                logger.warning("No news, skipping morning post")
                return
            extra = _enrich_news_with_body(news)
            content = generate_buildup_post(news, extra_context=extra)
            post_type = "buildup"

        image_url = _get_article_image(news) or generate_image(post_type)
        _publish(post_type, content, image_url, news)
        logger.info("=== Morning job done ===")
    except Exception:
        logger.exception("Morning job failed")


def run_spotlight_job():
    logger.info("=== Spotlight job started ===")
    try:
        fetch_all_news()
        news = get_unused_news(limit=6)
        player = random.choice(STAR_PLAYERS)
        extra = _enrich_news_with_body(news)
        content = generate_spotlight_post(news, player, extra_context=extra)
        # Ảnh bài báo ưu tiên, fallback Pexels query theo cầu thủ
        image_url = _get_article_image(news) or generate_image("spotlight", hint=player["query"])
        _publish("spotlight", content, image_url, news)
        logger.info("=== Spotlight job done (player=%s) ===", player["name"])
    except Exception:
        logger.exception("Spotlight job failed")


def run_drama_job():
    logger.info("=== Drama job started ===")
    try:
        fetch_all_news()
        news = get_unused_news(limit=8)
        if not news:
            logger.warning("No news, skipping drama post")
            return
        extra = _enrich_news_with_body(news)
        content = generate_drama_post(news, extra_context=extra)
        image_url = _get_article_image(news) or generate_image("drama")
        _publish("drama", content, image_url, news)
        logger.info("=== Drama job done ===")
    except Exception:
        logger.exception("Drama job failed")


def run_factoid_job():
    logger.info("=== Factoid job started ===")
    try:
        fetch_all_news()
        news = get_unused_news(limit=6)
        extra = _enrich_news_with_body(news)
        content = generate_factoid_post(news, extra_context=extra)
        image_url = _get_article_image(news) or generate_image("factoid")
        _publish("factoid", content, image_url, news)
        logger.info("=== Factoid job done ===")
    except Exception:
        logger.exception("Factoid job failed")


def run_debate_job():
    logger.info("=== Debate job started ===")
    try:
        fetch_all_news()
        news = get_unused_news(limit=6)
        extra = _enrich_news_with_body(news)
        content = generate_debate_post(news, extra_context=extra)
        image_url = _get_article_image(news) or generate_image("debate")
        _publish("debate", content, image_url, news)
        logger.info("=== Debate job done ===")
    except Exception:
        logger.exception("Debate job failed")


def run_evening_job():
    logger.info("=== Evening job started ===")
    try:
        matches = get_today_matches()
        fetch_all_news()
        news = get_unused_news(limit=4)

        if _has_matches_tonight(matches):
            extra = _enrich_news_with_body(news)
            content = generate_evening_post(matches, news, extra_context=extra)
            post_type = "evening"
        else:
            if not news:
                logger.warning("No news, skipping evening post")
                return
            extra = _enrich_news_with_body(news)
            content = generate_buildup_post(news, extra_context=extra)
            post_type = "buildup"

        image_url = _get_article_image(news) or generate_image(post_type)
        _publish(post_type, content, image_url, news)
        logger.info("=== Evening job done ===")
    except Exception:
        logger.exception("Evening job failed")
