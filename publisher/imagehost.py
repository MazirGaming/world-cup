"""Upload local card PNG -> public URL (cần cho Threads & Facebook).

Ưu tiên: domain riêng (nếu cấu hình env), fallback catbox.moe (free, không cần key).
"""
import logging
import os
import shutil
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Nếu bot lưu card vào thư mục web-served của domain riêng:
#   CARD_PUBLIC_DIR=/home/uXXX/public_html/cards
#   CARD_PUBLIC_BASE_URL=https://yourdomain.com/cards
PUBLIC_DIR = os.getenv("CARD_PUBLIC_DIR", "")
PUBLIC_BASE_URL = os.getenv("CARD_PUBLIC_BASE_URL", "").rstrip("/")

CATBOX_API = "https://catbox.moe/user/api.php"


def upload_public(local_path: str) -> Optional[str]:
    if not local_path or not os.path.exists(local_path):
        return None

    # 1) Domain riêng (ổn định nhất nếu có)
    if PUBLIC_DIR and PUBLIC_BASE_URL:
        try:
            os.makedirs(PUBLIC_DIR, exist_ok=True)
            fname = os.path.basename(local_path)
            shutil.copy2(local_path, os.path.join(PUBLIC_DIR, fname))
            url = f"{PUBLIC_BASE_URL}/{fname}"
            logger.info("Card hosted on domain: %s", url)
            return url
        except Exception as e:
            logger.warning("Domain host failed (%s), falling back to catbox", e)

    # 2) Fallback: catbox.moe
    try:
        with open(local_path, "rb") as f:
            resp = httpx.post(
                CATBOX_API,
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (os.path.basename(local_path), f, "image/png")},
                timeout=30,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("http"):
            logger.info("Card uploaded to catbox: %s", url)
            return url
        logger.warning("Catbox unexpected response: %s", url[:120])
        return None
    except Exception as e:
        logger.error("Image upload failed: %s", e)
        return None
