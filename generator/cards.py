"""Sinh social card có thương hiệu từ dữ liệu bài viết (Pillow).

Ảnh luôn khớp nội dung, không dùng ảnh bản quyền. Output PNG 1200x630.
"""
import logging
import os
import httpx
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE, "assets", "fonts")
FLAG_DIR = os.path.join(BASE, "assets", "flags")
CARD_DIR = os.path.join(BASE, "cards")
os.makedirs(FLAG_DIR, exist_ok=True)
os.makedirs(CARD_DIR, exist_ok=True)

W, H = 1200, 630

# Reverse map: Unicode bold (𝗔) -> ASCII (A), để Anton render được tiêu đề
_BOLD = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
_PLAIN = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
_UNBOLD_MAP = {ord(b): p for b, p in zip(_BOLD, _PLAIN)}


def _unbold(text: str) -> str:
    return (text or "").translate(_UNBOLD_MAP)

# Brand palette
BG_TOP = (12, 17, 31)
BG_BOTTOM = (24, 32, 56)
GOLD = (255, 200, 61)
GREEN = (46, 204, 113)
RED = (231, 76, 60)
WHITE = (245, 247, 250)
MUTED = (150, 162, 184)
PANEL = (30, 40, 66)
BRAND = "TRAM WORLD CUP"

# Team name -> ISO 3166-1 alpha-2 (flagcdn). Covers common WC nations + aliases.
TEAM_CODES = {
    "argentina": "ar", "brazil": "br", "france": "fr", "england": "gb-eng",
    "scotland": "gb-sct", "wales": "gb-wls", "northern ireland": "gb-nir",
    "portugal": "pt", "spain": "es", "germany": "de", "italy": "it",
    "netherlands": "nl", "holland": "nl", "belgium": "be", "croatia": "hr",
    "uruguay": "uy", "colombia": "co", "mexico": "mx", "united states": "us",
    "usa": "us", "united states of america": "us", "canada": "ca",
    "japan": "jp", "south korea": "kr", "korea republic": "kr", "korea": "kr",
    "australia": "au", "morocco": "ma", "senegal": "sn", "ghana": "gh",
    "nigeria": "ng", "cameroon": "cm", "ivory coast": "ci", "cote d'ivoire": "ci",
    "côte d'ivoire": "ci", "egypt": "eg", "denmark": "dk", "switzerland": "ch",
    "poland": "pl", "serbia": "rs", "norway": "no", "sweden": "se",
    "ecuador": "ec", "peru": "pe", "chile": "cl", "paraguay": "py",
    "saudi arabia": "sa", "qatar": "qa", "iran": "ir", "ir iran": "ir",
    "austria": "at", "turkey": "tr", "türkiye": "tr", "turkiye": "tr",
    "ukraine": "ua", "greece": "gr", "czechia": "cz", "czech republic": "cz",
    "bosnia-herzegovina": "ba", "bosnia and herzegovina": "ba",
    "south africa": "za", "cape verde": "cv", "panama": "pa", "costa rica": "cr",
    "jamaica": "jm", "honduras": "hn", "venezuela": "ve", "bolivia": "bo",
    "tunisia": "tn", "algeria": "dz", "mali": "ml", "new zealand": "nz",
    "uzbekistan": "uz", "jordan": "jo", "iraq": "iq", "uae": "ae",
    "united arab emirates": "ae", "slovenia": "si", "slovakia": "sk",
    "hungary": "hu", "romania": "ro", "ireland": "ie", "finland": "fi",
    "congo dr": "cd", "dr congo": "cd", "democratic republic of congo": "cd",
    "congo": "cg", "haiti": "ht", "curacao": "cw", "curaçao": "cw",
    "el salvador": "sv", "guatemala": "gt", "trinidad and tobago": "tt",
    "angola": "ao", "zambia": "zm", "kenya": "ke", "uganda": "ug",
    "burkina faso": "bf", "gabon": "ga", "north macedonia": "mk",
    "georgia": "ge", "albania": "al", "montenegro": "me", "thailand": "th",
    "vietnam": "vn", "china": "cn", "india": "in", "indonesia": "id",
    "oman": "om", "bahrain": "bh", "kuwait": "kw", "palestine": "ps",
    "lebanon": "lb", "syria": "sy", "south sudan": "ss", "mozambique": "mz",
    "equatorial guinea": "gq", "guinea": "gn", "benin": "bj", "namibia": "na",
}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _f_title(size):  return _font("Anton-Regular.ttf", size)
def _f_score(size):  return _font("Anton-Regular.ttf", size)
def _f_team(size):   return _font("Barlow-Bold.ttf", size)
def _f_meta(size):   return _font("Barlow-Medium.ttf", size)
def _f_black(size):  return _font("Barlow-Black.ttf", size)


def _gradient_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    # Diagonal gold accent (tốc độ / thể thao)
    draw.polygon([(0, H), (0, H - 14), (W, H - 60), (W, H - 46)], fill=GOLD)
    return img


def _logo_mark(draw, cx, cy, r=15):
    """Chấm tròn vàng làm logo (tránh tofu emoji)."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
    draw.ellipse([cx - r + 5, cy - r + 5, cx + r - 5, cy + r - 5], fill=(8, 12, 22))


def _brand_bar(draw: ImageDraw.ImageDraw, right_label: str = ""):
    draw.rectangle([0, 0, W, 70], fill=(8, 12, 22))
    _logo_mark(draw, 50, 35)
    draw.text((76, 35), BRAND, font=_f_black(30), fill=GOLD, anchor="lm")
    if right_label:
        draw.text((W - 40, 35), right_label, font=_f_meta(26), fill=MUTED, anchor="rm")


def _team_code(name: str):
    return TEAM_CODES.get((name or "").strip().lower())


def _flag(code: str, height: int):
    """Tải + cache cờ quốc gia (flagcdn). Trả về Image hoặc None."""
    if not code:
        return None
    path = os.path.join(FLAG_DIR, f"{code}.png")
    try:
        if not os.path.exists(path):
            resp = httpx.get(f"https://flagcdn.com/w320/{code}.png", timeout=8)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
        flag = Image.open(path).convert("RGBA")
        ratio = height / flag.height
        return flag.resize((int(flag.width * ratio), height), Image.LANCZOS)
    except Exception as e:
        logger.warning("Flag error %s: %s", code, e)
        return None


def _badge(draw, cx, cy, name: str, size: int):
    """Huy hiệu tròn chứa 3 chữ cái đầu khi không có cờ."""
    r = size // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PANEL, outline=GOLD, width=3)
    initials = "".join(w[0] for w in name.split()[:3]).upper()[:3] or "?"
    draw.text((cx, cy), initials, font=_f_black(int(size * 0.4)), fill=WHITE, anchor="mm")


def _draw_flag_or_badge(img, draw, cx, cy, name, flag_h):
    flag = _flag(_team_code(name), flag_h)
    if flag:
        fw = flag.width
        img.paste(flag, (int(cx - fw / 2), int(cy - flag_h / 2)), flag)
        draw.rectangle([cx - fw / 2, cy - flag_h / 2, cx + fw / 2, cy + flag_h / 2],
                       outline=(0, 0, 0), width=2)
    else:
        _badge(draw, cx, cy, name, flag_h)


def _save(img: Image.Image, name: str) -> str:
    path = os.path.join(CARD_DIR, f"{name}.png")
    img.save(path, "PNG", optimize=True)
    logger.info("Card saved: %s", path)
    return path


def _fit(draw, text, font_name, max_size, min_size, max_width):
    """Giảm cỡ chữ cho vừa chiều rộng."""
    size = max_size
    while size > min_size:
        font = _font(font_name, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return _font(font_name, min_size)


# ----------------------------- Public renderers -----------------------------

def render_results_card(matches: list) -> str:
    """Card tổng kết kết quả (tối đa 5 trận đã FINISHED)."""
    finished = [m for m in matches if m.get("home_score") is not None][:5]
    if not finished:
        return ""
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)
    _brand_bar(draw, "FULL-TIME RESULTS")
    draw.text((40, 110), "RESULTS", font=_f_title(64), fill=WHITE, anchor="lm")
    draw.text((W - 40, 120), "WORLD CUP 2026", font=_f_meta(28), fill=GOLD, anchor="rm")

    rows = finished
    top, bottom = 180, H - 40
    gap = (bottom - top) / len(rows)
    for i, m in enumerate(rows):
        cy = int(top + gap * i + gap / 2)
        draw.rounded_rectangle([40, cy - gap / 2 + 8, W - 40, cy + gap / 2 - 8],
                               radius=14, fill=PANEL)
        fh = int(min(54, gap - 36))
        _draw_flag_or_badge(img, draw, 100, cy, m["home"], fh)
        _draw_flag_or_badge(img, draw, W - 100, cy, m["away"], fh)
        hf = _fit(draw, m["home"].upper(), "Barlow-Bold.ttf", 34, 20, 270)
        af = _fit(draw, m["away"].upper(), "Barlow-Bold.ttf", 34, 20, 270)
        draw.text((180, cy), m["home"].upper(), font=hf, fill=WHITE, anchor="lm")
        draw.text((W - 185, cy), m["away"].upper(), font=af, fill=WHITE, anchor="rm")
        score = f"{m['home_score']} - {m['away_score']}"
        draw.text((W / 2, cy), score, font=_f_score(min(48, fh + 4)), fill=GOLD, anchor="mm")
    return _save(img, "results")


def render_fixtures_card(matches: list, title: str = "TODAY'S FIXTURES") -> str:
    """Card lịch thi đấu sắp tới (tối đa 5 trận)."""
    upcoming = [m for m in matches if m.get("home_score") is None][:5]
    if not upcoming:
        return ""
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)
    _brand_bar(draw, "UPCOMING")
    draw.text((40, 110), title, font=_f_title(56), fill=WHITE, anchor="lm")
    draw.text((W - 40, 120), "WORLD CUP 2026", font=_f_meta(28), fill=GOLD, anchor="rm")

    top, bottom = 180, H - 40
    gap = (bottom - top) / len(upcoming)
    for i, m in enumerate(upcoming):
        cy = int(top + gap * i + gap / 2)
        draw.rounded_rectangle([40, cy - gap / 2 + 8, W - 40, cy + gap / 2 - 8],
                               radius=14, fill=PANEL)
        fh = int(min(50, gap - 36))
        _draw_flag_or_badge(img, draw, 100, cy, m["home"], fh)
        _draw_flag_or_badge(img, draw, W - 100, cy, m["away"], fh)
        hf = _fit(draw, m["home"].upper(), "Barlow-Bold.ttf", 30, 18, 250)
        af = _fit(draw, m["away"].upper(), "Barlow-Bold.ttf", 30, 18, 250)
        draw.text((180, cy), m["home"].upper(), font=hf, fill=WHITE, anchor="lm")
        draw.text((W - 185, cy), m["away"].upper(), font=af, fill=WHITE, anchor="rm")
        utc = m.get("utc_date", "")
        kickoff = utc[11:16] + " UTC" if len(utc) >= 16 else "VS"
        draw.text((W / 2, cy), kickoff, font=_f_team(30), fill=GOLD, anchor="mm")
    return _save(img, "fixtures")


def render_breaking_card(headline: str, category: str = "BREAKING") -> str:
    """Card tin nóng: badge + headline lớn trên nền tối."""
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)
    # Dải brand
    draw.rectangle([0, 0, W, 70], fill=(8, 12, 22))
    _logo_mark(draw, 50, 35)
    draw.text((76, 35), BRAND, font=_f_black(30), fill=GOLD, anchor="lm")
    draw.text((W - 40, 35), "WORLD CUP 2026", font=_f_meta(26), fill=MUTED, anchor="rm")

    bw = draw.textlength(category, font=_f_black(40)) + 60
    draw.rounded_rectangle([40, 150, 40 + bw, 220], radius=10, fill=RED)
    draw.text((40 + bw / 2, 185), category, font=_f_black(40), fill=WHITE, anchor="mm")

    # Headline wrap (tối đa 3 dòng) — bỏ emoji/ký tự Anton không render được
    clean = "".join(c for c in _unbold(headline) if c.isascii())
    words = clean.upper().split()
    lines, cur = [], ""
    font = _f_title(72)
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= W - 80 or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:3]

    y = 290
    for line in lines:
        draw.text((40, y), line, font=font, fill=WHITE, anchor="lm")
        y += 84
    return _save(img, "breaking")
