import logging
import os
import random
import httpx
from datetime import date
from typing import Optional
from openai import OpenAI
from storage.database import NewsItem

WORLD_CUP_START = date(2026, 6, 11)

_BOLD_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
)

STAR_PLAYERS = [
    {"name": "Cristiano Ronaldo", "team": "Bồ Đào Nha", "query": "Cristiano Ronaldo soccer"},
    {"name": "Lionel Messi", "team": "Argentina", "query": "Lionel Messi football"},
    {"name": "Kylian Mbappé", "team": "Pháp", "query": "Mbappe soccer France"},
    {"name": "Vinicius Jr", "team": "Brazil", "query": "Vinicius Jr soccer Brazil"},
    {"name": "Erling Haaland", "team": "Na Uy", "query": "Haaland soccer Norway"},
    {"name": "Jude Bellingham", "team": "Anh", "query": "Bellingham soccer England"},
    {"name": "Lamine Yamal", "team": "Tây Ban Nha", "query": "Yamal soccer Spain"},
    {"name": "Harry Kane", "team": "Anh", "query": "Harry Kane soccer England"},
    {"name": "Pedri", "team": "Tây Ban Nha", "query": "Pedri soccer Spain"},
    {"name": "Neymar Jr", "team": "Brazil", "query": "Neymar soccer Brazil"},
]


def to_bold(text: str) -> str:
    return text.translate(_BOLD_MAP)


def days_until_wc() -> int:
    delta = WORLD_CUP_START - date.today()
    return max(0, delta.days)


def apply_formatting(content: str) -> str:
    lines = content.split("\n")
    if not lines:
        return content
    lines[0] = to_bold(lines[0])
    lines.insert(1, "━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TEXT_MODEL = "gpt-4o-mini"
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

SYSTEM_PROMPT = """Bạn là biên tập viên thể thao cho fanpage bóng đá Việt Nam mùa World Cup 2026.
Phong cách: sôi nổi, táo bạo, ngắn gọn, có emoji phù hợp.

QUY TẮC BẮT BUỘC:
- Dòng ĐẦU TIÊN: tiêu đề IN HOA, dưới 12 từ, emoji, giật gân
- Nội dung: 80-120 từ — NGẮN GỌN, không dài dòng, không liệt kê dài
- NGHIÊM CẤM bịa tỉ số, thẻ đỏ/vàng, kết quả, hay sự kiện cụ thể không có trong dữ liệu đầu vào
- Nếu dữ liệu không đủ → phân tích/góc nhìn, KHÔNG đặt ra sự kiện giả
- Kết thúc bằng 1 câu hỏi ngắn kích thích comment
- Dòng CUỐI: #WorldCup2026 #TramWorldCup #BongDa"""

IMAGE_QUERIES = {
    "morning": ["world cup soccer match", "football stadium celebration", "soccer goal crowd"],
    "evening": ["football stadium night lights", "soccer match evening", "world cup fans night"],
    "drama": ["soccer referee red card", "football VAR review", "soccer players arguing"],
    "buildup": ["world cup trophy 2026", "soccer fans excitement", "football stadium USA"],
    "spotlight": ["soccer star portrait", "football player stadium", "soccer world cup player"],
    "factoid": ["football stadium aerial view", "world cup host city", "soccer stadium architecture"],
    "debate": ["soccer fans debate", "football supporters rival", "soccer stadium atmosphere"],
    "heatcheck": ["soccer night celebration", "football fans late night", "world cup night game"],
}


def generate_morning_post(matches: list[dict], news_items: list[NewsItem], extra_context: str = "") -> str:
    if not matches and not news_items:
        return ""
    matches_text = _format_matches(matches) if matches else "Không có trận đấu đêm qua."
    news_text = _format_news(news_items)
    prompt = f"""Viết bài Facebook buổi sáng tổng kết World Cup 2026.

KẾT QUẢ ĐÊM QUA (CHỈ dùng dữ liệu này, không thêm chi tiết):
{matches_text}

TIN TỨC:
{news_text}{extra_context}

Yêu cầu: Tổng kết đúng kết quả trên, nêu 1-2 điểm nổi bật, KHÔNG thêm thẻ đỏ/vàng/drama nếu không có trong dữ liệu."""
    return _call_openai(prompt)


def generate_evening_post(matches: list[dict], news_items: list[NewsItem], extra_context: str = "") -> str:
    if not matches:
        return ""
    matches_text = _format_matches(matches)
    news_text = _format_news(news_items)
    prompt = f"""Viết bài Facebook preview các trận World Cup 2026 tối nay.

CÁC TRẬN TỐI NAY:
{matches_text}

TIN TỨC:
{news_text}{extra_context}

Yêu cầu: Preview ngắn từng cặp đấu, dự đoán 1 trận hot nhất, tạo không khí hứng khởi."""
    return _call_openai(prompt)


def generate_drama_post(news_items: list[NewsItem], extra_context: str = "") -> str:
    if not news_items:
        return ""
    news_text = _format_news(news_items)
    prompt = f"""Viết bài Facebook drama/tranh cãi về World Cup 2026.

TIN TỨC (CHỈ dùng thông tin này — không bịa thêm sự kiện):
{news_text}{extra_context}

Yêu cầu:
- Chọn ĐÚNG 1 sự kiện có thật trong tin tức trên
- 2 luồng ý kiến đối lập rõ ràng
- Tone mạnh, kích thích tranh luận
- Kết: "Bạn đứng về phía nào? 👇" """
    return _call_openai(prompt)


def generate_spotlight_post(news_items: list[NewsItem], player: dict, extra_context: str = "") -> str:
    news_text = _format_news(news_items)
    days_left = days_until_wc()
    countdown = f"⏳ Còn {days_left} ngày đến World Cup 2026!" if days_left > 0 else "🔥 World Cup 2026 đang diễn ra!"
    name = player["name"]
    team = player["team"]

    prompt = f"""Viết bài Facebook spotlight về {name} ({team}) tại World Cup 2026.

{countdown}

TIN TỨC LIÊN QUAN (dùng nếu có nhắc đến {name}):
{news_text}{extra_context}

Yêu cầu:
- Tập trung vào {name}: phong độ, kỳ vọng, lịch sử WC
- Nếu không có tin tức về cầu thủ này → dùng kiến thức thực tế, KHÔNG bịa kết quả trận đấu
- Có thể nhắc rivalry (Ronaldo vs Messi) nếu tạo thêm drama tự nhiên
- Câu hỏi cuối: liên quan trực tiếp đến {name}"""
    return _call_openai(prompt)


def generate_factoid_post(news_items: list[NewsItem], extra_context: str = "") -> str:
    news_text = _format_news(news_items)
    days_left = days_until_wc()
    countdown = f"⏳ Còn {days_left} ngày đến World Cup 2026!" if days_left > 0 else "🔥 World Cup 2026 đang diễn ra!"

    topics = [
        "sân vận động đăng cai WC 2026 (MetLife, Rose Bowl, Azteca, SoFi...)",
        "các thành phố đăng cai ở Mỹ/Canada/Mexico — thông tin thú vị",
        "kỷ lục và thống kê đặc biệt về World Cup qua các năm",
        "FIFA và chủ tịch Gianni Infantino — quyết định gây tranh cãi",
        "thể thức 48 đội lần đầu tiên trong lịch sử WC",
        "thông tin vé, múi giờ, lịch phát sóng tại Việt Nam",
    ]
    topic = random.choice(topics)

    prompt = f"""Viết bài Facebook "fact thú vị" về World Cup 2026.

{countdown}

CHỦ ĐỀ: {topic}

TIN TỨC (ưu tiên dùng nếu liên quan):
{news_text}{extra_context}

Yêu cầu:
- Thông tin phải CHÍNH XÁC — dùng kiến thức thực tế về WC 2026, không suy đoán
- Phong cách "wow, bạn có biết không?" — hấp dẫn, ngắn gọn
- Kết bằng câu hỏi hoặc bình chọn"""
    return _call_openai(prompt)


def generate_debate_post(news_items: list[NewsItem], extra_context: str = "") -> str:
    news_text = _format_news(news_items)

    debate_topics = [
        "Ronaldo hay Messi: ai xứng đáng có World Cup hơn?",
        "VAR đang cứu bóng đá hay phá hỏng bóng đá?",
        "World Cup 48 đội: hay hơn hay loãng chất hơn?",
        "Ai sẽ vô địch WC 2026: Brazil, Pháp hay Argentina?",
        "Mbappé: thiên tài thực sự hay chỉ được thổi phồng?",
        "Nên xem World Cup ở rạp, quán nhậu hay ở nhà?",
    ]

    prompt = f"""Viết bài Facebook dạng TRANH LUẬN 2 phe về World Cup 2026.

TIN TỨC (dùng nếu có chủ đề tranh luận thực tế hay hơn):
{news_text}{extra_context}

CHỦ ĐỀ GỢI Ý (chọn 1, hoặc dùng chủ đề từ tin tức nếu hot hơn):
{chr(10).join(f'- {t}' for t in debate_topics)}

Định dạng BẮT BUỘC:
- Tiêu đề là câu hỏi gây tranh cãi IN HOA
- 🔵 TEAM A: 2-3 lý do ngắn, mạnh
- 🔴 TEAM B: 2-3 lý do ngắn, mạnh
- Kết: "Comment 🔵 hoặc 🔴 bên dưới!" """
    return _call_openai(prompt)


def generate_buildup_post(news_items: list[NewsItem], extra_context: str = "") -> str:
    news_text = _format_news(news_items)
    days_left = days_until_wc()
    countdown = f"⏳ Còn {days_left} ngày đến World Cup 2026!" if days_left > 0 else "🔥 World Cup 2026 đã bắt đầu!"

    prompt = f"""Viết bài Facebook về không khí chuẩn bị cho World Cup 2026.

{countdown}

TIN TỨC (chỉ viết về thông tin có trong đây):
{news_text}{extra_context}

Yêu cầu:
- Dựa vào tin tức thực tế, không bịa thêm sự kiện
- Tạo cảm giác hứng khởi, háo hức
- Kết bằng câu hỏi tương tác"""
    return _call_openai(prompt)


def generate_image(post_type: str, hint: str = "") -> Optional[str]:
    query = hint if hint else random.choice(IMAGE_QUERIES.get(post_type, IMAGE_QUERIES["morning"]))
    try:
        resp = httpx.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos and hint:
            return generate_image(post_type)
        if not photos:
            logger.warning("No Pexels photos found for query: %s", query)
            return None
        url = random.choice(photos)["src"]["large2x"]
        logger.info("Pexels image [%s] query=%s", post_type, query)
        return url
    except Exception as e:
        logger.error("Pexels error: %s", e)
        return None


def _call_openai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            max_tokens=600,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return apply_formatting(content)
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
    return "\n".join(f"- [{item.source}] {item.title}" for item in news_items[:8])
