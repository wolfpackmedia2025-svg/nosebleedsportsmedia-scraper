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
import urllib.parse

# X's public bearer token (embedded in their own web client)
X_BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I7ssbmtoEw%3D1Ts0im8aBi5pZRSzsXS3ECzJNQVJPvs0Apna9GRf0r8rJG8Sb3"


def get_guest_token() -> Optional[str]:
    """Get a guest token from X's public API."""
    try:
        req = urllib.request.Request(
            "https://api.twitter.com/1.1/guest/activate.json",
            data=b"",
            method="POST",
            headers={
                "Authorization": f"Bearer {X_BEARER}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("guest_token")
    except Exception as e:
        logger.warning(f"Failed to get guest token: {e}")
        return None


def fetch_user_followers(handle: str, guest_token: str) -> Optional[int]:
    """Fetch follower count for a single handle using X's public API."""
    try:
        url = f"https://api.twitter.com/1.1/users/show.json?screen_name={handle}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {X_BEARER}",
            "x-guest-token": guest_token,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("followers_count")
    except Exception as e:
        logger.debug(f"Failed to get followers for @{handle}: {e}")
        return None


def scrape_all_followers() -> list:
    """Fetch follower counts for all accounts using X's public API."""
    results = []
    guest_token = get_guest_token()

    for acc in ACCOUNTS:
        count = None
        if guest_token:
            count = fetch_user_followers(acc["handle"], guest_token)

        if count is not None:
            results.append({**acc, "followers": count, "formatted": format_count(count)})
        else:
            results.append({**acc, "followers": None, "formatted": None})

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
