import logging
import httpx
from config.settings import (
    FACEBOOK_PAGE_ID,
    FACEBOOK_ACCESS_TOKEN,
    FACEBOOK_API_BASE,
    DRY_RUN,
)

logger = logging.getLogger(__name__)


def publish_post(content: str, image_url: str | None = None) -> str | None:
    if not content:
        logger.warning("Empty content, skipping publish")
        return None

    if DRY_RUN:
        logger.info("[DRY RUN] Would publish (image=%s):\n%s", bool(image_url), content)
        return "dry_run_post_id"

    if image_url:
        return _publish_with_photo(content, image_url)
    return _publish_text(content)


def _publish_with_photo(content: str, image_url: str) -> str | None:
    url = f"{FACEBOOK_API_BASE}/{FACEBOOK_PAGE_ID}/photos"
    try:
        resp = httpx.post(
            url,
            data={"caption": content, "url": image_url, "access_token": FACEBOOK_ACCESS_TOKEN},
            timeout=30,
        )
        resp.raise_for_status()
        post_id = resp.json().get("post_id") or resp.json().get("id")
        logger.info("Published Facebook photo post: %s", post_id)
        return post_id
    except httpx.HTTPStatusError as e:
        logger.error("Facebook photo API error %s: %s", e.response.status_code, e.response.text)
        return None
    except httpx.HTTPError as e:
        logger.error("Facebook request error: %s", e)
        return None


def _publish_text(content: str) -> str | None:
    url = f"{FACEBOOK_API_BASE}/{FACEBOOK_PAGE_ID}/feed"
    try:
        resp = httpx.post(
            url,
            data={"message": content, "access_token": FACEBOOK_ACCESS_TOKEN},
            timeout=15,
        )
        resp.raise_for_status()
        post_id = resp.json().get("id")
        logger.info("Published Facebook text post: %s", post_id)
        return post_id
    except httpx.HTTPStatusError as e:
        logger.error("Facebook API error %s: %s", e.response.status_code, e.response.text)
        return None
    except httpx.HTTPError as e:
        logger.error("Facebook request error: %s", e)
        return None
