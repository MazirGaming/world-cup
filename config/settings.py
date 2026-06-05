import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
FOOTBALL_API_KEY = os.environ["FOOTBALL_API_KEY"]
FACEBOOK_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
FACEBOOK_ACCESS_TOKEN = os.environ["FACEBOOK_ACCESS_TOKEN"]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

FOOTBALL_API_BASE = "https://api.football-data.org/v4"
FACEBOOK_API_BASE = "https://graph.facebook.com/v21.0"
THREADS_API_BASE = "https://graph.threads.net/v1.0"

# Threads (optional — bỏ trống để tắt)
THREADS_USER_ID = os.getenv("THREADS_USER_ID", "")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN", "")

# World Cup 2026 competition ID on football-data.org
WORLD_CUP_COMPETITION_ID = "WC"

NEWS_FEEDS = [
    "https://www.goal.com/feeds/en/news",
    "https://www.espn.com/espn/rss/soccer/news",
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.skysports.com/rss/12040",
    "https://www.theguardian.com/football/rss",
    "https://www.marca.com/en/rss/football/international.xml",
]

# Schedule (Vietnam time UTC+7)
SCHEDULE_MORNING = "07:00"    # Tổng kết kết quả đêm qua
SCHEDULE_SPOTLIGHT = "09:00"  # Spotlight cầu thủ ngôi sao
SCHEDULE_DRAMA = "11:00"      # Drama / tranh cãi
SCHEDULE_FACTOID = "13:30"    # Fact thú vị / sân / nước đăng cai
SCHEDULE_DEBATE = "15:30"     # Tranh luận 2 phe
SCHEDULE_EVENING = "18:00"    # Preview trận tối nay
