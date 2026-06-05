import logging
import time
import httpx
from typing import Optional
from config.settings import THREADS_USER_ID, THREADS_ACCESS_TOKEN, DRY_RUN

logger = logging.getLogger(__name__)

THREADS_API_BASE = "https://graph.threads.net/v1.0"
THREADS_MAX_CHARS = 490
THREADS_HASHTAGS = "#WorldCup2026 #BongDa"


def publish_to_threads(content: str, image_url: Optional[str] = None) -> Optional[str]:
    if not THREADS_USER_ID or not THREADS_ACCESS_TOKEN:
        logger.info("Threads not configured (missing THREADS_USER_ID or THREADS_ACCESS_TOKEN), skipping")
        return None
    if not content:
        return None

    if DRY_RUN:
        logger.info("[DRY RUN] Would post to Threads:\n%s", content[:120])
        return "dry_run_threads_id"

    text = _trim_for_threads(content)

    container_id = _create_container(text, image_url)
    if not container_id:
        return None

    # Threads yêu cầu chờ tối thiểu vài giây trước khi publish
    time.sleep(3)

    return _publish_container(container_id)


def _trim_for_threads(content: str) -> str:
    """Cắt gọn nội dung cho Threads (tối đa 490 ký tự + hashtags)."""
    # Bỏ hashtag cuối bài (sẽ thêm lại phiên bản ngắn)
    lines = content.split("\n")
    # Dòng cuối thường là hashtag dài — loại bỏ
    if lines and lines[-1].startswith("#"):
        lines = lines[:-1]
    body = "\n".join(lines).strip()

    suffix = f"\n\n{THREADS_HASHTAGS}"
    max_body = THREADS_MAX_CHARS - len(suffix)

    if len(body) <= max_body:
        return body + suffix

    # Cắt ở ranh giới câu gần nhất
    truncated = body[:max_body]
    last_period = max(truncated.rfind("。"), truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "), truncated.rfind(".\n"))
    if last_period > max_body // 2:
        truncated = truncated[: last_period + 1]
    else:
        truncated = truncated.rstrip() + "..."

    return truncated + suffix


def _create_container(text: str, image_url: Optional[str]) -> Optional[str]:
    url = f"{THREADS_API_BASE}/{THREADS_USER_ID}/threads"
    data: dict = {
        "access_token": THREADS_ACCESS_TOKEN,
        "text": text,
    }
    if image_url:
        data["media_type"] = "IMAGE"
        data["image_url"] = image_url
    else:
        data["media_type"] = "TEXT"

    try:
        resp = httpx.post(url, data=data, timeout=20)
        resp.raise_for_status()
        container_id = resp.json().get("id")
        logger.info("Threads container created: %s", container_id)
        return container_id
    except httpx.HTTPStatusError as e:
        logger.error("Threads create error %s: %s", e.response.status_code, e.response.text)
        return None
    except httpx.HTTPError as e:
        logger.error("Threads request error: %s", e)
        return None


def _publish_container(container_id: str) -> Optional[str]:
    url = f"{THREADS_API_BASE}/{THREADS_USER_ID}/threads_publish"
    try:
        resp = httpx.post(
            url,
            data={"creation_id": container_id, "access_token": THREADS_ACCESS_TOKEN},
            timeout=20,
        )
        resp.raise_for_status()
        post_id = resp.json().get("id")
        logger.info("Published Threads post: %s", post_id)
        return post_id
    except httpx.HTTPStatusError as e:
        logger.error("Threads publish error %s: %s", e.response.status_code, e.response.text)
        return None
    except httpx.HTTPError as e:
        logger.error("Threads publish request error: %s", e)
        return None
