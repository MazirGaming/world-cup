"""Resolve real, content-relevant images from Wikipedia/Wikimedia + flags."""
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "TramWorldCupBot/1.0 (https://tramworldcup; contact admin)"}

# ISO-3166 alpha-2 codes (flagcdn) for common football nations
COUNTRY_CODES = {
    "argentina": "ar", "brazil": "br", "france": "fr", "england": "gb-eng",
    "scotland": "gb-sct", "wales": "gb-wls", "portugal": "pt", "spain": "es",
    "germany": "de", "italy": "it", "netherlands": "nl", "belgium": "be",
    "croatia": "hr", "uruguay": "uy", "colombia": "co", "mexico": "mx",
    "united states": "us", "usa": "us", "canada": "ca", "japan": "jp",
    "south korea": "kr", "korea": "kr", "australia": "au", "morocco": "ma",
    "senegal": "sn", "ghana": "gh", "nigeria": "ng", "cameroon": "cm",
    "ivory coast": "ci", "egypt": "eg", "denmark": "dk", "switzerland": "ch",
    "poland": "pl", "serbia": "rs", "norway": "no", "sweden": "se",
    "ecuador": "ec", "peru": "pe", "chile": "cl", "paraguay": "py",
    "saudi arabia": "sa", "qatar": "qa", "iran": "ir", "austria": "at",
    "turkey": "tr", "ukraine": "ua", "greece": "gr",
}


def wikipedia_image(title: str) -> Optional[str]:
    """Lấy ảnh chính của một trang Wikipedia (cầu thủ/đội/sân...)."""
    if not title:
        return None
    try:
        resp = httpx.get(
            WIKI_API,
            params={
                "action": "query",
                "titles": title,
                "prop": "pageimages",
                "piprop": "original|thumbnail",
                "pithumbsize": 1200,
                "format": "json",
                "redirects": 1,
            },
            headers=HEADERS,
            timeout=8,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            for key in ("original", "thumbnail"):
                src = page.get(key, {}).get("source")
                if src and not src.lower().endswith(".svg"):
                    logger.info("Wikipedia image for '%s'", title)
                    return src
        return None
    except Exception as e:
        logger.warning("Wikipedia image error for '%s': %s", title, e)
        return None


def country_flag(text: str) -> Optional[str]:
    """Trả về cờ quốc gia (PNG) nếu chuỗi chứa tên quốc gia đã biết."""
    if not text:
        return None
    low = text.lower()
    for name, code in COUNTRY_CODES.items():
        if name in low:
            return f"https://flagcdn.com/w1280/{code}.png"
    return None
