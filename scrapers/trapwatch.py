"""
TrapWatch scraper using Scrapling.
Fetches live trap board data from trapwatch.app
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TRAPWATCH_URL = "https://trapwatch.app/#/"

TRAP_CATEGORIES = {
    "trap_city": {"label": "Trap City", "emoji": "🏙️", "color": "red",
                  "description": "Heavy public action on one side, sharp money on the other."},
    "trap_detected": {"label": "Trap Detected", "emoji": "⚠️", "color": "yellow",
                      "description": "Active trap behavior confirmed by line movement."},
    "trap_potential": {"label": "Trap Potential", "emoji": "👀", "color": "blue",
                       "description": "Early signs of a trap forming — watch these."},
}


def scrape_trapwatch() -> dict:
    """
    Scrape live trap board from trapwatch.app.
    Returns categorized trap games.
    """
    try:
        from scrapling.fetchers import DynamicFetcher

        page = DynamicFetcher.fetch(
            TRAPWATCH_URL,
            headless=True,
            network_idle=True,
            timeout=30,
        )

        traps = {
            "trap_city": [],
            "trap_detected": [],
            "trap_potential": [],
            "no_longer_trap": [],
        }

        # Find section headers and their associated game rows
        # TrapWatch uses section labels to categorize games
        full_text = page.get_all_text() if hasattr(page, "get_all_text") else str(page)

        # Try to find game rows
        game_rows = page.css("[class*='game'], [class*='trap'], [class*='matchup']", adaptive=True)

        current_section = None
        for row in game_rows:
            row_text = row.text.strip() if hasattr(row, "text") else str(row)
            if not row_text:
                continue

            # Detect section based on nearby heading
            if "trap city" in row_text.lower():
                current_section = "trap_city"
                continue
            elif "trap detected" in row_text.lower():
                current_section = "trap_detected"
                continue
            elif "trap potential" in row_text.lower():
                current_section = "trap_potential"
                continue
            elif "no longer" in row_text.lower():
                current_section = "no_longer_trap"
                continue

            if current_section and current_section in traps:
                traps[current_section].append({"text": row_text[:200]})

        return traps

    except Exception as e:
        logger.warning(f"Failed to scrape TrapWatch: {e}")
        return {}


def get_mock_traps() -> dict:
    """Fallback mock data that mirrors TrapWatch structure."""
    return {
        "trap_city": [
            {"teams": "Sabres vs Devils", "pick": "Sabres +1.5", "line": "-270", "time": "7:10 PM ET", "sport": "NHL"},
            {"teams": "Knights vs Oilers", "pick": "Golden Knights +1.5", "line": "-194", "time": "10:10 PM ET", "sport": "NHL"},
            {"teams": "Ducks vs Canucks", "pick": "Ducks +1.5", "line": "-238", "time": "10:40 PM ET", "sport": "NHL"},
        ],
        "trap_detected": [
            {"teams": "Celtics vs Pacers", "pick": "Total 133.5: Over", "line": "-114", "time": "7:00 PM ET", "sport": "NBA"},
        ],
        "trap_potential": [
            {"teams": "Warriors vs Grizzlies", "pick": "Total 225.5: Over", "line": "-192", "time": "7:00 PM ET", "sport": "NBA"},
            {"teams": "Oilers vs Kings", "pick": "Oilers", "line": "-130", "time": "10:40 PM ET", "sport": "NHL"},
            {"teams": "Suns vs Jazz", "pick": "Total 135.5: Over", "line": "-119", "time": "9:00 PM ET", "sport": "NBA"},
        ],
        "last_updated": "",
    }
