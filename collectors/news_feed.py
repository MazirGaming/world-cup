import logging
import feedparser
import httpx
from bs4 import BeautifulSoup
from config.settings import NEWS_FEEDS
from storage.database import is_news_seen, save_news_items

logger = logging.getLogger(__name__)

WORLD_CUP_KEYWORDS = [
    "world cup", "fifa", "2026", "mundial",
    "goal", "penalty", "red card", "var", "offside",
]


def fetch_all_news() -> list[dict]:
    all_items = []
    for feed_url in NEWS_FEEDS:
        items = _fetch_feed(feed_url)
        all_items.extend(items)

    new_items = [i for i in all_items if not is_news_seen(i["url"])]
    if new_items:
        save_news_items(new_items)
        logger.info("Saved %d new news items", len(new_items))

    return new_items


def _fetch_feed(feed_url: str) -> list[dict]:
    try:
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries:
            title = entry.get("title", "")
            url = entry.get("link", "")
            summary = entry.get("summary", "")

            if not _is_world_cup_related(title + " " + summary):
                continue

            items.append({
                "title": title,
                "url": url,
                "summary": _clean_html(summary),
                "source": feed.feed.get("title", feed_url),
            })
        return items
    except Exception as e:
        logger.error("Feed error %s: %s", feed_url, e)
        return []


def fetch_article_content(url: str) -> str:
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; WorldCupBot/1.0)"
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs[:10])
        return text[:2000]
    except Exception as e:
        logger.warning("Could not fetch article %s: %s", url, e)
        return ""


def _is_world_cup_related(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in WORLD_CUP_KEYWORDS)


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator=" ", strip=True)[:500]
