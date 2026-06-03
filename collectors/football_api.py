import logging
from datetime import date, timedelta
import httpx
from config.settings import FOOTBALL_API_KEY, FOOTBALL_API_BASE, WORLD_CUP_COMPETITION_ID

logger = logging.getLogger(__name__)

HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY}


def get_yesterday_matches() -> list[dict]:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    return _get_matches(yesterday, yesterday)


def get_today_matches() -> list[dict]:
    today = date.today().isoformat()
    return _get_matches(today, today)


def _get_matches(date_from: str, date_to: str) -> list[dict]:
    url = f"{FOOTBALL_API_BASE}/competitions/{WORLD_CUP_COMPETITION_ID}/matches"
    try:
        resp = httpx.get(
            url,
            headers=HEADERS,
            params={"dateFrom": date_from, "dateTo": date_to},
            timeout=10,
        )
        resp.raise_for_status()
        matches = resp.json().get("matches", [])
        return [_parse_match(m) for m in matches]
    except httpx.HTTPError as e:
        logger.error("Football API error: %s", e)
        return []


def get_standings() -> list[dict]:
    url = f"{FOOTBALL_API_BASE}/competitions/{WORLD_CUP_COMPETITION_ID}/standings"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        standings = resp.json().get("standings", [])
        groups = []
        for group in standings:
            groups.append({
                "group": group.get("group", ""),
                "table": [
                    {
                        "position": row["position"],
                        "team": row["team"]["name"],
                        "played": row["playedGames"],
                        "points": row["points"],
                        "goal_diff": row["goalDifference"],
                    }
                    for row in group.get("table", [])[:4]
                ],
            })
        return groups
    except httpx.HTTPError as e:
        logger.error("Standings API error: %s", e)
        return []


def _parse_match(m: dict) -> dict:
    score = m.get("score", {})
    full_time = score.get("fullTime", {})
    return {
        "home": m["homeTeam"]["name"],
        "away": m["awayTeam"]["name"],
        "home_score": full_time.get("home"),
        "away_score": full_time.get("away"),
        "status": m.get("status"),
        "utc_date": m.get("utcDate"),
        "stage": m.get("stage"),
        "group": m.get("group"),
    }
