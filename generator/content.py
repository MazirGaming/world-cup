import json
import logging
import os
import random
import httpx
from datetime import date
from typing import Optional, Tuple
from openai import OpenAI
from storage.database import NewsItem

WORLD_CUP_START = date(2026, 6, 11)

_BOLD_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
)

# name, team, Wikipedia article title (for accurate photos)
STAR_PLAYERS = [
    {"name": "Cristiano Ronaldo", "team": "Portugal", "wiki": "Cristiano Ronaldo"},
    {"name": "Lionel Messi", "team": "Argentina", "wiki": "Lionel Messi"},
    {"name": "Kylian Mbappé", "team": "France", "wiki": "Kylian Mbappé"},
    {"name": "Vinicius Junior", "team": "Brazil", "wiki": "Vinícius Júnior"},
    {"name": "Erling Haaland", "team": "Norway", "wiki": "Erling Haaland"},
    {"name": "Jude Bellingham", "team": "England", "wiki": "Jude Bellingham"},
    {"name": "Lamine Yamal", "team": "Spain", "wiki": "Lamine Yamal"},
    {"name": "Harry Kane", "team": "England", "wiki": "Harry Kane"},
    {"name": "Pedri", "team": "Spain", "wiki": "Pedri"},
    {"name": "Rodrygo", "team": "Brazil", "wiki": "Rodrygo"},
]


def to_bold(text: str) -> str:
    return text.translate(_BOLD_MAP)


def days_until_wc() -> int:
    return max(0, (WORLD_CUP_START - date.today()).days)


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

SYSTEM_PROMPT = """You are a sharp, energetic football editor for the World Cup 2026 fanpage "Tram World Cup".
Write engaging posts in ENGLISH.

You MUST reply with ONLY valid JSON in this exact shape:
{"post": "<the full post text>", "image_subject": "<best photo subject>"}

Rules for "post":
- First line: a punchy ALL-CAPS headline, under 12 words, with a fitting emoji
- Body: 70-110 words, concise and punchy — NO filler, no long lists
- NEVER invent scores, cards, results, injuries, quotes, or events not in the provided data
- If data is thin, give analysis/angle — do NOT fabricate facts
- End with ONE short question that drives comments
- Last line EXACTLY: #WorldCup2026 #TramWorldCup #Football

Rules for "image_subject":
- The single most relevant REAL subject for an accompanying photo, as an English Wikipedia article title
- Prefer a specific person (e.g. "Cristiano Ronaldo"), then a team ("Brazil national football team"), stadium, or country
- Be specific to the post's actual topic — never generic like "soccer" or "football"
"""

IMAGE_QUERIES = {
    "morning": ["world cup soccer match", "football stadium celebration", "soccer goal crowd"],
    "evening": ["football stadium night lights", "soccer match evening", "world cup fans night"],
    "drama": ["soccer referee decision", "football VAR review", "soccer players reaction"],
    "buildup": ["world cup trophy 2026", "soccer fans excitement", "football stadium USA"],
    "spotlight": ["soccer star action", "football player stadium", "world cup player"],
    "factoid": ["football stadium aerial", "world cup host city", "soccer stadium architecture"],
    "debate": ["soccer fans crowd", "football supporters", "soccer stadium atmosphere"],
}


def generate_morning_post(matches: list, news_items: list, extra_context: str = "") -> Tuple[str, str]:
    if not matches and not news_items:
        return "", ""
    matches_text = _format_matches(matches) if matches else "No matches last night."
    prompt = f"""Write a morning recap post for World Cup 2026.

RESULTS LAST NIGHT (use ONLY this data, add nothing):
{matches_text}

NEWS:
{_format_news(news_items)}{extra_context}

Recap the results above accurately, highlight 1-2 standout moments. Do NOT add cards/drama not in the data."""
    return _call_openai(prompt)


def generate_evening_post(matches: list, news_items: list, extra_context: str = "") -> Tuple[str, str]:
    if not matches:
        return "", ""
    prompt = f"""Write an evening preview post for tonight's World Cup 2026 matches.

TONIGHT'S MATCHES:
{_format_matches(matches)}

NEWS:
{_format_news(news_items)}{extra_context}

Preview each fixture briefly, predict the hottest one, build excitement."""
    return _call_openai(prompt)


def generate_drama_post(news_items: list, extra_context: str = "") -> Tuple[str, str]:
    if not news_items:
        return "", ""
    angles = [
        "a controversial refereeing / VAR decision",
        "a bold statement or interview from a player or manager",
        "a surprising form swing, injury, or selection call",
        "a tactical or lineup controversy",
        "an off-pitch story (fans, FIFA, host-city, scheduling)",
    ]
    angle = random.choice(angles)
    prompt = f"""Write a debate-driving "hot topic" post about World Cup 2026, based ONLY on the news below.

NEWS (use only what's here — do not fabricate events):
{_format_news(news_items)}{extra_context}

Instructions:
- Pick the single most interesting REAL story, ideally around: {angle}
- Do NOT default to a Ronaldo-vs-Messi comparison unless the news is specifically about that
- Present two genuinely opposing viewpoints, sharp and provocative but fact-based
- End: "Whose side are you on? 👇" """
    return _call_openai(prompt)


def generate_spotlight_post(news_items: list, player: dict, extra_context: str = "") -> Tuple[str, str]:
    name, team = player["name"], player["team"]
    prompt = f"""Write a player spotlight post about {name} ({team}) at World Cup 2026.

RELATED NEWS (use if it mentions {name}):
{_format_news(news_items)}{extra_context}

Instructions:
- Focus on {name}: current form, expectations, World Cup story
- If there's no news about this player, use well-known real facts — do NOT invent match results or quotes
- Closing question must be directly about {name}"""
    post, _ = _call_openai(prompt)
    # Override image subject with the player's exact Wikipedia title for accurate photo
    return post, player["wiki"]


def generate_factoid_post(news_items: list, extra_context: str = "") -> Tuple[str, str]:
    days_left = days_until_wc()
    status = f"⏳ {days_left} days to World Cup 2026!" if days_left > 0 else "🔥 World Cup 2026 is underway!"
    topics = [
        "a host stadium (MetLife, Rose Bowl, Azteca, SoFi, AT&T...) and what makes it special",
        "a host city in the USA/Canada/Mexico — surprising facts",
        "a special World Cup record or statistic across history",
        "FIFA and president Gianni Infantino — a notable or controversial decision",
        "the first-ever 48-team format and what it changes",
        "tickets, time zones, or how Vietnam fans can watch",
    ]
    topic = random.choice(topics)
    prompt = f"""Write a "did you know?" fact post about World Cup 2026.

{status}

TOPIC: {topic}

NEWS (use if relevant):
{_format_news(news_items)}{extra_context}

Instructions:
- Facts MUST be accurate — use real knowledge about WC 2026, do not speculate
- "Wow, did you know?" tone — engaging and concise
- End with a question or poll"""
    return _call_openai(prompt)


def generate_debate_post(news_items: list, extra_context: str = "") -> Tuple[str, str]:
    topics = [
        "Who deserves to win WC 2026: Brazil, France, Argentina, England or Spain?",
        "Is VAR saving or ruining football?",
        "48 teams: better spectacle or watered-down quality?",
        "Is Mbappé already the best player in the world?",
        "Will an underdog nation shock the World Cup this year?",
        "Best young star of the tournament so far?",
    ]
    prompt = f"""Write a two-sided DEBATE post about World Cup 2026.

NEWS (use a real debate from here if hotter):
{_format_news(news_items)}{extra_context}

SUGGESTED TOPICS (pick one, or use a hotter topic from the news):
{chr(10).join(f'- {t}' for t in topics)}

Required format:
- Headline = a provocative question in ALL CAPS
- 🔵 SIDE A: 2-3 short, strong points
- 🔴 SIDE B: 2-3 short, strong points
- End: "Comment 🔵 or 🔴 below!" """
    return _call_openai(prompt)


def generate_buildup_post(news_items: list, extra_context: str = "") -> Tuple[str, str]:
    days_left = days_until_wc()
    status = f"⏳ {days_left} days to World Cup 2026!" if days_left > 0 else "🔥 World Cup 2026 is underway!"
    prompt = f"""Write a post about the World Cup 2026 atmosphere.

{status}

NEWS (only write about info present here):
{_format_news(news_items)}{extra_context}

Base it on the real news above, build excitement, end with an engaging question."""
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
            logger.warning("No Pexels photos for query: %s", query)
            return None
        url = random.choice(photos)["src"]["large2x"]
        logger.info("Pexels image [%s] query=%s", post_type, query)
        return url
    except Exception as e:
        logger.error("Pexels error: %s", e)
        return None


def _call_openai(prompt: str) -> Tuple[str, str]:
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            max_tokens=700,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        post = (data.get("post") or "").strip()
        subject = (data.get("image_subject") or "").strip()
        if not post:
            return "", ""
        return apply_formatting(post), subject
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        return "", ""


def _format_matches(matches: list) -> str:
    lines = []
    for m in matches:
        if m["home_score"] is not None:
            lines.append(f"- {m['home']} {m['home_score']}-{m['away_score']} {m['away']}")
        else:
            time_str = m.get("utc_date", "")[:16].replace("T", " ") if m.get("utc_date") else ""
            lines.append(f"- {m['home']} vs {m['away']} ({time_str} UTC)")
    return "\n".join(lines) if lines else "No matches."


def _format_news(news_items: list) -> str:
    if not news_items:
        return "No fresh news."
    return "\n".join(f"- [{item.source}] {item.title}" for item in news_items[:8])
