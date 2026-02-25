"""
Nosebleed Sports Media — Scrapling Microservice
Provides live follower counts, X feed, and odds for nosebleedsportsmedia.com
"""
import os
import time
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------
follower_cache = TTLCache(maxsize=1, ttl=3600)    # 1 hour
feed_cache     = TTLCache(maxsize=1, ttl=900)     # 15 minutes
odds_cache     = TTLCache(maxsize=1, ttl=300)     # 5 minutes

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://nosebleedsportsmedia.com,http://localhost:3000").split(",")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🕷️  Scrapling service starting up...")
    yield
    logger.info("Scrapling service shutting down.")

app = FastAPI(
    title="Nosebleed Sports Scraping Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "nosebleed-scraper"}


@app.get("/followers")
def get_followers(force: bool = Query(False)):
    """
    Returns follower counts for all 13 Wolfpack Media X accounts.
    Cached for 1 hour. Pass ?force=true to bypass cache.
    """
    cache_key = "followers"
    if not force and cache_key in follower_cache:
        return {"data": follower_cache[cache_key], "cached": True}

    from scrapers.twitter import scrape_all_followers
    data = scrape_all_followers()
    follower_cache[cache_key] = data
    return {"data": data, "cached": False}


@app.get("/feed")
def get_feed(
    handles: Optional[str] = Query(None, description="Comma-separated handles"),
    force: bool = Query(False),
):
    """
    Returns recent X posts from Wolfpack Media accounts.
    Cached for 15 minutes.
    """
    cache_key = f"feed_{handles or 'all'}"
    if not force and cache_key in feed_cache:
        return {"tweets": feed_cache[cache_key], "source": "scrapling", "cached": True}

    from scrapers.twitter import scrape_feed, ACCOUNTS

    handle_list = handles.split(",") if handles else [a["handle"] for a in ACCOUNTS[:6]]
    tweets = scrape_feed(handle_list)

    if not tweets:
        # Return mock data as fallback
        from scrapers.twitter import ACCOUNTS as ALL_ACCOUNTS
        tweets = _mock_feed(handle_list)
        source = "mock_fallback"
    else:
        source = "scrapling"

    feed_cache[cache_key] = tweets
    return {"tweets": tweets, "source": source, "cached": False}


@app.get("/trapwatch")
def get_trapwatch(force: bool = Query(False)):
    """
    Returns live trap board data from TrapWatch.
    Cached for 10 minutes.
    """
    trap_cache = TTLCache(maxsize=1, ttl=600)
    cache_key = "trapwatch"
    if not force and cache_key in trap_cache:
        return {"traps": trap_cache[cache_key], "cached": True}

    from scrapers.trapwatch import scrape_trapwatch, get_mock_traps
    data = scrape_trapwatch()

    if not data or all(len(v) == 0 for v in data.values() if isinstance(v, list)):
        data = get_mock_traps()
        source = "mock_fallback"
    else:
        source = "scrapling"

    trap_cache[cache_key] = data
    return {"traps": data, "source": source, "cached": False}


@app.get("/whistlewatch")
def get_whistlewatch(force: bool = Query(False)):
    """Returns trending plays and leaderboard from WhistleWatch.ai. Cached 15 min."""
    ww_cache = TTLCache(maxsize=1, ttl=900)
    cache_key = "whistlewatch"
    if not force and cache_key in ww_cache:
        return {"data": ww_cache[cache_key], "cached": True}

    from scrapers.whistlewatch import scrape_whistlewatch, get_mock_whistlewatch
    data = scrape_whistlewatch()

    if not data or not data.get("plays"):
        data = get_mock_whistlewatch()
        source = "mock_fallback"
    else:
        source = "scrapling"

    ww_cache[cache_key] = data
    return {"data": data, "source": source, "cached": False}


@app.get("/odds")
def get_odds(
    sports: Optional[str] = Query("nfl,nba,mlb", description="Comma-separated sports"),
    force: bool = Query(False),
):
    """
    Returns current betting odds for requested sports.
    Cached for 5 minutes.
    """
    cache_key = f"odds_{sports}"
    if not force and cache_key in odds_cache:
        return {"games": odds_cache[cache_key], "cached": True}

    from scrapers.odds import scrape_all_odds, get_mock_odds

    sport_list = [s.strip() for s in sports.split(",")]
    games = scrape_all_odds(sport_list)

    if not games:
        games = get_mock_odds()
        source = "mock_fallback"
    else:
        source = "scrapling"

    odds_cache[cache_key] = games
    return {"games": games, "source": source, "cached": False}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_feed(handles: list) -> list:
    mock = [
        {"id": "m1", "handle": "NosebleedHQ", "sport": "All Sports", "text": "Thunder DOMINATE Lakers 118-98 — SGA drops 38 🔥", "time": "2h ago", "likes": 847, "retweets": 203},
        {"id": "m2", "handle": "NosebleedHoops", "sport": "Basketball", "text": "Celtics -3.5 first half is the play tonight 🍀", "time": "3h ago", "likes": 412, "retweets": 89},
        {"id": "m3", "handle": "BaseballBros", "sport": "Baseball", "text": "Yankees lineup this spring is absolutely stacked 💪⚾", "time": "4h ago", "likes": 623, "retweets": 145},
        {"id": "m4", "handle": "Nosebleedfooty", "sport": "Soccer", "text": "Arsenal top of the table after that 90th minute winner 😤", "time": "5h ago", "likes": 1204, "retweets": 387},
        {"id": "m5", "handle": "LatestGolfHQ", "sport": "Golf", "text": "Scottie Scheffler shoots 63 in Round 2 ⛳", "time": "6h ago", "likes": 334, "retweets": 67},
        {"id": "m6", "handle": "NosebleedPuck", "sport": "Hockey", "text": "Avalanche on a 7-game win streak. MacKinnon COOKING 🏒", "time": "7h ago", "likes": 521, "retweets": 112},
    ]
    return [t for t in mock if t["handle"] in handles] or mock


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
