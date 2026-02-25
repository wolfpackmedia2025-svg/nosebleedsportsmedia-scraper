"""
X/Twitter scraper using Scrapling.
Scrapes profile follower counts and recent posts.
"""
import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ACCOUNTS = [
    {"handle": "NosebleedHQ", "sport": "All Sports"},
    {"handle": "NosebleedHoops", "sport": "Basketball"},
    {"handle": "BaseballBros", "sport": "Baseball"},
    {"handle": "baseball_NBS", "sport": "Baseball"},
    {"handle": "Nosebleedfooty", "sport": "Soccer"},
    {"handle": "NosebleedPuck", "sport": "Hockey"},
    {"handle": "CasualBigTen", "sport": "College Football"},
    {"handle": "LatestGolfHQ", "sport": "Golf"},
    {"handle": "NosebleedGI", "sport": "Football"},
    {"handle": "SportsDigestHQ", "sport": "All Sports"},
    {"handle": "BigLeagueDigest", "sport": "Baseball"},
    {"handle": "AthleteSwag", "sport": "Athlete Lifestyle"},
    {"handle": "itsmichaelJ", "sport": "Personality"},
]


def format_count(n: int) -> str:
    """Format a number as 1.2K, 4.5M, etc."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


import urllib.request
import time


def fetch_user_followers_fxtwitter(handle: str) -> Optional[int]:
    """
    Fetch follower count using fxtwitter's public API.
    No API key required.
    """
    try:
        url = f"https://api.fxtwitter.com/{handle}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NosebleedSports/1.0)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("user", {}).get("followers")
    except Exception as e:
        logger.debug(f"Failed to get followers for @{handle}: {e}")
        return None


def scrape_all_followers() -> list:
    """Fetch real follower counts for all accounts via fxtwitter."""
    results = []
    for acc in ACCOUNTS:
        count = fetch_user_followers_fxtwitter(acc["handle"])
        if count is not None:
            results.append({**acc, "followers": count, "formatted": format_count(count)})
        else:
            results.append({**acc, "followers": None, "formatted": None})
        time.sleep(0.3)  # be nice to the API
    return results


def scrape_feed(handles: list[str], count_per_account: int = 2) -> list:
    """
    Scrape recent posts from X accounts.
    Uses Scrapling StealthyFetcher with adaptive mode.
    """
    tweets = []
    try:
        from scrapling.fetchers import StealthyFetcher

        for handle in handles[:6]:  # limit to top 6 to avoid rate limits
            try:
                url = f"https://x.com/{handle}"
                page = StealthyFetcher.fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    timeout=30,
                )

                # Extract tweet articles from the timeline
                tweet_articles = page.css('article[data-testid="tweet"]', auto_save=True)

                for article in tweet_articles[:count_per_account]:
                    try:
                        # Get tweet text
                        text_el = article.css('[data-testid="tweetText"]')
                        text = text_el.text if text_el else ""
                        if not text:
                            continue

                        # Get like and retweet counts
                        like_el = article.css('[data-testid="like"] span span')
                        rt_el = article.css('[data-testid="retweet"] span span')
                        likes = _parse_count(like_el.text if like_el else "0")
                        retweets = _parse_count(rt_el.text if rt_el else "0")

                        # Get time
                        time_el = article.css('time')
                        time_str = time_el.attrib.get("datetime", "") if time_el else ""

                        tweets.append({
                            "id": f"{handle}_{len(tweets)}",
                            "handle": handle,
                            "sport": next((a["sport"] for a in ACCOUNTS if a["handle"] == handle), "Sports"),
                            "text": text,
                            "time": _format_time(time_str),
                            "likes": likes,
                            "retweets": retweets,
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing tweet: {e}")
                        continue

            except Exception as e:
                logger.warning(f"Failed to scrape feed for @{handle}: {e}")
                continue

    except ImportError:
        logger.error("Scrapling not installed")

    return tweets


def _parse_count(text: str) -> int:
    """Parse '1.2K' or '4M' style counts to int."""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    try:
        if text.endswith("K"):
            return int(float(text[:-1]) * 1_000)
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        return int(text)
    except Exception:
        return 0


def _format_time(iso_str: str) -> str:
    """Convert ISO datetime to a relative time string."""
    if not iso_str:
        return ""
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        hours = int(diff.total_seconds() / 3600)
        if hours < 1:
            mins = int(diff.total_seconds() / 60)
            return f"{mins}m ago"
        if hours < 24:
            return f"{hours}h ago"
        return f"{diff.days}d ago"
    except Exception:
        return ""
