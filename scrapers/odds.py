"""
Sports odds scraper using Scrapling.
Scrapes current betting lines from ESPN and Action Network.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

SPORT_URLS = {
    "nfl": "https://www.espn.com/nfl/odds",
    "nba": "https://www.espn.com/nba/odds",
    "mlb": "https://www.espn.com/mlb/odds",
    "nhl": "https://www.espn.com/nhl/odds",
    "ncaaf": "https://www.espn.com/college-football/odds",
}

SPORT_EMOJI = {
    "nfl": "🏈",
    "nba": "🏀",
    "mlb": "⚾",
    "nhl": "🏒",
    "ncaaf": "🎓🏈",
}


def scrape_espn_odds(sport: str) -> list:
    """Scrape odds for a sport from ESPN."""
    url = SPORT_URLS.get(sport)
    if not url:
        return []

    try:
        from scrapling.fetchers import DynamicFetcher

        page = DynamicFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            timeout=30,
        )

        games = []

        # ESPN odds table rows
        rows = page.css(".Odds__Table tr, .odds-cell, [class*='OddsTable'] tr", adaptive=True)
        if not rows:
            # Try alternative selectors
            rows = page.css("tr.Table__TR", adaptive=True)

        for row in rows[:10]:
            try:
                cells = row.css("td")
                if len(cells) < 3:
                    continue

                text_content = row.text_content if hasattr(row, 'text_content') else row.text
                if not text_content or len(str(text_content).strip()) < 5:
                    continue

                # Try to extract team names and lines
                team_els = row.css(".Odds__Team, .team-name, [class*='Team']", adaptive=True)
                teams = [el.text.strip() for el in team_els if el.text.strip()]

                line_els = row.css(".Odds__Line, .odds-line, [class*='Line']", adaptive=True)
                lines = [el.text.strip() for el in line_els if el.text.strip()]

                if teams:
                    games.append({
                        "sport": sport,
                        "emoji": SPORT_EMOJI.get(sport, "🏆"),
                        "teams": teams[:2],
                        "lines": lines[:3],
                        "raw": str(text_content)[:200],
                    })
            except Exception as e:
                logger.debug(f"Error parsing odds row: {e}")
                continue

        return games

    except Exception as e:
        logger.warning(f"Failed to scrape {sport} odds: {e}")
        return []


def scrape_all_odds(sports: Optional[list] = None) -> list:
    """Scrape odds for multiple sports."""
    if sports is None:
        sports = ["nfl", "nba", "mlb"]

    all_games = []
    for sport in sports:
        games = scrape_espn_odds(sport)
        all_games.extend(games)

    return all_games


def get_mock_odds() -> list:
    """Fallback mock odds data."""
    return [
        {"sport": "nba", "emoji": "🏀", "teams": ["Thunder", "Lakers"], "spread": "OKC -4.5", "total": "O/U 224.5", "moneyline": "OKC -185"},
        {"sport": "mlb", "emoji": "⚾", "teams": ["Yankees", "Red Sox"], "spread": "NYY -1.5", "total": "O/U 9.0", "moneyline": "NYY -130"},
        {"sport": "nfl", "emoji": "🏈", "teams": ["Chiefs", "Raiders"], "spread": "KC -7", "total": "O/U 46.5", "moneyline": "KC -310"},
        {"sport": "nhl", "emoji": "🏒", "teams": ["Avalanche", "Blues"], "spread": "COL -1.5", "total": "O/U 6.5", "moneyline": "COL -165"},
        {"sport": "nba", "emoji": "🏀", "teams": ["Celtics", "Knicks"], "spread": "BOS -3", "total": "O/U 218.5", "moneyline": "BOS -150"},
        {"sport": "mlb", "emoji": "⚾", "teams": ["Dodgers", "Giants"], "spread": "LAD -1.5", "total": "O/U 8.5", "moneyline": "LAD -145"},
    ]
