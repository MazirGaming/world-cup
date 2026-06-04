import logging
import os
import random
import httpx
from datetime import date
from typing import Optional
from openai import OpenAI
from storage.database import NewsItem

WORLD_CUP_START = date(2026, 6, 11)
HASHTAGS = "#WorldCup2026 #TramWorldCup #BongDa #FIFA2026 #Football"


def days_until_wc() -> int:
    delta = WORLD_CUP_START - date.today()
    return max(0, delta.days)

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TEXT_MODEL = "gpt-4o-mini"
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

SYSTEM_PROMPT = """Bạn là biên tập viên thể thao cho một fanpage bóng đá Việt Nam trong mùa World Cup 2026.
Phong cách viết: sôi nổi, gần gũi, dùng tiếng Việt thân thiện, có thể dùng emoji phù hợp.
Yêu cầu:
- Dòng ĐẦU TIÊN phải là tiêu đề GIẬT GÂN, IN HOA, ngắn gọn dưới 15 từ, dùng emoji bắt mắt
- Tiếp theo là nội dung bài viết
- Viết cho độc giả Việt Nam, nhưng giữ tên cầu thủ/đội bóng theo tên quốc tế
- Nội dung phải dựa trên sự kiện có thật, không bịa đặt
- Không xúc phạm cá nhân, không kỳ thị, không vi phạm pháp luật
- Độ dài phần nội dung: 150-250 từ, phù hợp Facebook
- Kết thúc bài bằng câu hỏi tương tác để tăng comment
- Dòng CUỐI CÙNG chỉ gồm các hashtag: #WorldCup2026 #TramWorldCup #BongDa #FIFA2026 #Football"""

IMAGE_QUERIES = {
    "morning": ["world cup soccer celebration", "football stadium crowd", "soccer goal celebration"],
    "evening": ["soccer match preview", "football stadium night", "world cup fans"],
    "drama": ["soccer referee decision", "football controversy", "var review soccer"],
    "buildup": ["world cup stadium 2026", "soccer fans excitement", "football world cup trophy", "world cup host city"],
}


def generate_morning_post(matches: list[dict], news_items: list[NewsItem]) -> str:
    if not matches and not news_items:
        return ""

    matches_text = _format_matches(matches) if matches else "Không có trận đấu nào đêm qua."
    news_text = _format_news(news_items)

    prompt = f"""Viết bài Facebook buổi sáng tổng kết World Cup 2026.

KẾT QUẢ ĐÊM QUA:
{matches_text}

TIN TỨC NỔI BẬT:
{news_text}

Yêu cầu: Dòng đầu tiêu đề giật gân IN HOA, tổng hợp kết quả, highlight quan trọng, kết thúc câu hỏi tương tác."""

    return _call_openai(prompt)


def generate_evening_post(matches: list[dict], news_items: list[NewsItem]) -> str:
    if not matches:
        return ""

    matches_text = _format_matches(matches)
    news_text = _format_news(news_items)

    prompt = f"""Viết bài Facebook buổi chiều preview các trận World Cup 2026 tối nay.

CÁC TRẬN TỐI NAY:
{matches_text}

TIN TỨC LIÊN QUAN:
{news_text}

Yêu cầu: Dòng đầu tiêu đề giật gân IN HOA, phân tích nhẹ từng cặp đấu, dự đoán kết quả, tạo không khí hứng khởi."""

    return _call_openai(prompt)


def generate_drama_post(news_items: list[NewsItem]) -> str:
    if not news_items:
        return ""

    news_text = _format_news(news_items)

    prompt = f"""Viết bài Facebook về chủ đề drama/tranh cãi nổi bật nhất World Cup 2026 hôm nay.

TIN TỨC:
{news_text}

Yêu cầu:
- Dòng đầu tiêu đề giật gân IN HOA, kích thích tò mò
- Chọn 1 sự kiện gây tranh cãi nhất (VAR, thẻ đỏ, phát ngôn HLV, drama cầu thủ...)
- Trình bày 2 luồng ý kiến đối lập
- Tone: kích thích tranh luận nhưng trung lập, dựa trên sự thật
- Kết thúc bằng câu hỏi "Bạn đứng về phía nào?"
- KHÔNG bịa đặt, KHÔNG xúc phạm cá nhân"""

    return _call_openai(prompt)


def generate_buildup_post(news_items: list[NewsItem]) -> str:
    news_text = _format_news(news_items)
    days_left = days_until_wc()
    countdown = f"⏳ Còn {days_left} ngày đến World Cup 2026!" if days_left > 0 else "🔥 World Cup 2026 đã bắt đầu!"

    prompt = f"""Viết bài Facebook về không khí chuẩn bị cho World Cup 2026 sắp diễn ra.

ĐẾM NGƯỢC: {countdown}



TIN TỨC LIÊN QUAN:
{news_text}

Chủ đề có thể chọn (ưu tiên cái có tin tức nhất):
- Thông tin sân vận động đăng cai (Mỹ, Canada, Mexico)
- Công bố danh sách cầu thủ / đội hình dự kiến các đội
- Thông tin vé, cách mua vé, giá vé
- CĐV chuẩn bị như thế nào, hành trình đi xem
- Trận giao hữu chuẩn bị của các đội
- Phát biểu đáng chú ý của HLV/cầu thủ trước giải
- Thống kê, lịch sử, kỷ lục World Cup thú vị

Yêu cầu:
- Dòng đầu tiêu đề GIẬT GÂN IN HOA, kích thích sự háo hức chờ đợi
- Nội dung hấp dẫn, tạo cảm giác hồi hộp đếm ngược đến World Cup
- Kết thúc bằng câu hỏi tương tác (đội yêu thích, dự đoán, kế hoạch xem...)
- KHÔNG bịa đặt, chỉ dùng thông tin từ tin tức đã cung cấp"""

    return _call_openai(prompt)


def generate_image(post_type: str) -> Optional[str]:
    queries = IMAGE_QUERIES.get(post_type, IMAGE_QUERIES["morning"])
    query = random.choice(queries)
    try:
        resp = httpx.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            logger.warning("No Pexels photos found for query: %s", query)
            return None
        photo = random.choice(photos)
        url = photo["src"]["large2x"]
        logger.info("Fetched Pexels image for %s: %s", post_type, url)
        return url
    except Exception as e:
        logger.error("Pexels error: %s", e)
        return None


def _call_openai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        logger.info("Generated post (%d chars)", len(content))
        return content
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        return ""


def _format_matches(matches: list[dict]) -> str:
    lines = []
    for m in matches:
        if m["home_score"] is not None:
            lines.append(f"- {m['home']} {m['home_score']}-{m['away_score']} {m['away']}")
        else:
            time_str = m.get("utc_date", "")[:16].replace("T", " ") if m.get("utc_date") else ""
            lines.append(f"- {m['home']} vs {m['away']} ({time_str} UTC)")
    return "\n".join(lines) if lines else "Không có trận đấu."


def _format_news(news_items: list[NewsItem]) -> str:
    if not news_items:
        return "Không có tin tức mới."
    lines = [f"- [{item.source}] {item.title}" for item in news_items[:6]]
    return "\n".join(lines)
