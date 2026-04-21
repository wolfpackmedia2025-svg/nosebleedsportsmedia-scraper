#!/usr/bin/env python3
"""
Mac mini scraper runner — fetches all live data and pushes to Vercel Blob.
Replaces the Railway FastAPI service. Run via cron.

Blob keys written:
  scraper/followers.json   — follower counts for all accounts
  scraper/trapwatch.json   — TrapWatch signals
  scraper/feed.json        — X/Twitter feed
  scraper/whistlewatch.json — WhistleWatch signals
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BLOB_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
BLOB_BASE  = "https://blob.vercel-storage.com"

def upload_blob(key: str, data: dict):
    """Upload JSON to Vercel Blob at a fixed key (no random suffix)."""
    import urllib.request
    payload = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BLOB_BASE}/{key}",
        data=payload,
        method="PUT",
        headers={
            "Authorization": f"Bearer {BLOB_TOKEN}",
            "Content-Type": "application/json",
            "x-add-random-suffix": "0",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            log.info(f"✅ Uploaded {key} → {result.get('url','?')}")
            return result.get("url")
    except Exception as e:
        log.error(f"❌ Failed to upload {key}: {e}")
        return None


def run_followers():
    log.info("📊 Scraping follower counts...")
    try:
        from scrapers.followers import scrape_followers
        data = scrape_followers()
    except Exception as e:
        log.error(f"Followers scraper failed: {e}")
        return
    upload_blob("scraper/followers.json", {"data": data, "updated_at": datetime.now(timezone.utc).isoformat()})


def run_trapwatch():
    log.info("🏙️  Scraping TrapWatch...")
    try:
        from scrapers.trapwatch import scrape_trapwatch
        data = scrape_trapwatch()
    except Exception as e:
        log.error(f"TrapWatch scraper failed: {e}")
        return
    upload_blob("scraper/trapwatch.json", {"traps": data, "updated_at": datetime.now(timezone.utc).isoformat()})


def run_feed():
    log.info("📰 Scraping X feed...")
    FEED_HANDLES = [
        "NosebleedHQ","NosebleedHoops","BaseballBros","baseball_NBS",
        "Nosebleedfooty","NosebleedPuck","CasualBigTen","LatestGolfHQ",
        "SportsDigestHQ","BigLeagueDigest","AthleteSwag",
    ]
    try:
        from scrapers.twitter import scrape_feed
        data = scrape_feed(FEED_HANDLES, count_per_account=2)
    except Exception as e:
        log.error(f"Feed scraper failed: {e}")
        return
    upload_blob("scraper/feed.json", {"tweets": data, "updated_at": datetime.now(timezone.utc).isoformat()})


def run_whistlewatch():
    log.info("🔔 Scraping WhistleWatch...")
    try:
        from scrapers.whistlewatch import scrape_whistlewatch
        data = scrape_whistlewatch()
    except Exception as e:
        log.error(f"WhistleWatch scraper failed: {e}")
        return
    upload_blob("scraper/whistlewatch.json", {"signals": data, "updated_at": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    if not BLOB_TOKEN:
        log.error("BLOB_READ_WRITE_TOKEN not set — cannot upload")
        sys.exit(1)

    log.info("🚀 Starting scraper run...")
    run_followers()
    run_trapwatch()
    run_feed()
    run_whistlewatch()
    log.info("✅ All scrapers done")
