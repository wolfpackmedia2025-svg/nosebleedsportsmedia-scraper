"""
TrapWatch scraper — reads live data directly from TrapWatch's Supabase backend.
No headless browser needed. Real data, updated every ~20 minutes by TrapWatch.
"""
import logging
import urllib.request
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SUPABASE_URL = "https://zpgmwnnrtjbbvmyqhkvu.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZ213bm5ydGpiYnZteXFoa3Z1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4MjEyMjIsImV4cCI6MjA4NTM5NzIyMn0"
    ".EjPPMK2zmMqmbXH4mtFrr9eQZGS5Ic6zj6AJrl9kxsg"
)

STATUS_MAP = {
    "trap city":     "trap_city",
    "trap detected": "trap_detected",
    "trap potential":"trap_potential",
}

SPORT_MAP = {
    "NHL": "NHL", "NBA": "NBA", "MLB": "MLB", "NFL": "NFL",
    "NCAAB": "NCAAB", "NCAAF": "NCAAF", "CFB": "NCAAF",
    "GOLF": "Golf", "SOC": "Soccer", "MLS": "Soccer",
}


def _fetch_today() -> list:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fields = "trap_status,matchup,sharp_selection,sharp_odds,league,time,odds,bets_pct,handle_pct,market,away_team_key,home_team_key"
    url = (
        f"{SUPABASE_URL}/rest/v1/trap_analysis"
        f"?analysis_date=eq.{today}"
        f"&game_state=eq.Scheduled"
        f"&select={fields}"
        f"&order=bets_pct.desc"
    )
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _format_row(row: dict) -> dict:
    away = row.get("away_team_key", "")
    home = row.get("home_team_key", "")
    teams = f"{away} vs {home}" if away and home else row.get("matchup", "")

    sharp = row.get("sharp_selection", "")
    sharp_odds = row.get("sharp_odds")
    odds_str = f"{sharp_odds:+d}" if isinstance(sharp_odds, (int, float)) else str(sharp_odds or "")

    sport = SPORT_MAP.get(row.get("league", "").upper(), row.get("league", ""))

    return {
        "teams": teams,
        "pick": sharp,
        "line": odds_str,
        "time": row.get("time", ""),
        "sport": sport,
        "market": row.get("market", ""),
        "bets_pct": row.get("bets_pct"),
        "handle_pct": row.get("handle_pct"),
        "public_side": row.get("matchup", "").split(" @ ")[1] if " @ " in row.get("matchup", "") else "",
    }


def scrape_trapwatch() -> dict:
    """Fetch live trap data from TrapWatch's Supabase. Returns categorized trap games."""
    try:
        rows = _fetch_today()
        traps: dict = {k: [] for k in STATUS_MAP.values()}
        traps["no_longer_trap"] = []

        for row in rows:
            status = row.get("trap_status", "").lower().strip()
            bucket = STATUS_MAP.get(status)
            if bucket:
                traps[bucket].append(_format_row(row))

        logger.info(
            f"TrapWatch: {len(traps['trap_city'])} Trap City, "
            f"{len(traps['trap_detected'])} Trap Detected, "
            f"{len(traps['trap_potential'])} Trap Potential"
        )
        return traps

    except Exception as e:
        logger.warning(f"TrapWatch Supabase fetch failed: {e}")
        return {}


def get_mock_traps() -> dict:
    """Fallback mock data — only used if Supabase is unreachable."""
    return {
        "trap_city": [
            {"teams": "Sabres vs Devils", "pick": "Sabres +1.5", "line": "-270", "time": "7:10 PM ET", "sport": "NHL"},
            {"teams": "Knights vs Oilers", "pick": "Golden Knights +1.5", "line": "-194", "time": "10:10 PM ET", "sport": "NHL"},
        ],
        "trap_detected": [
            {"teams": "Celtics vs Pacers", "pick": "Total Over 233.5", "line": "-114", "time": "7:00 PM ET", "sport": "NBA"},
        ],
        "trap_potential": [
            {"teams": "Warriors vs Grizzlies", "pick": "Total Over 225.5", "line": "-192", "time": "7:00 PM ET", "sport": "NBA"},
        ],
    }
