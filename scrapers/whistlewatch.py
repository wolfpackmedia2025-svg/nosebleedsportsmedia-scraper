"""
WhistleWatch.ai scraper using Scrapling.
Fetches trending plays, verdicts, and leaderboard data.
"""
import json
import logging

logger = logging.getLogger(__name__)

WHISTLEWATCH_URL = "https://whistlewatch.ai/"


def scrape_whistlewatch() -> dict:
    """Scrape live plays and verdicts from WhistleWatch.ai."""
    try:
        from scrapling.fetchers import DynamicFetcher

        page = DynamicFetcher.fetch(
            WHISTLEWATCH_URL,
            headless=True,
            network_idle=True,
            timeout=30,
        )

        plays = []
        leaderboard = []

        # Try to find play cards
        play_cards = page.css(
            "[class*='play'], [class*='card'], [class*='verdict'], article",
            adaptive=True
        )

        for card in play_cards[:10]:
            try:
                text = card.text.strip() if hasattr(card, "text") else ""
                if not text or len(text) < 10:
                    continue

                verdict = "MISSED CALL" if "missed" in text.lower() else \
                          "CORRECT CALL" if "correct" in text.lower() else "UNDER REVIEW"

                plays.append({
                    "text": text[:300],
                    "verdict": verdict,
                })
            except Exception:
                continue

        # Try leaderboard
        lb_rows = page.css(
            "[class*='leaderboard'] tr, [class*='leader'] li",
            adaptive=True
        )
        for row in lb_rows[:5]:
            try:
                text = row.text.strip() if hasattr(row, "text") else ""
                if text:
                    leaderboard.append({"text": text[:100]})
            except Exception:
                continue

        return {"plays": plays, "leaderboard": leaderboard}

    except Exception as e:
        logger.warning(f"Failed to scrape WhistleWatch: {e}")
        return {}


def get_mock_whistlewatch() -> dict:
    """Fallback mock data mirroring WhistleWatch structure."""
    return {
        "trending": [
            {
                "id": "1",
                "teams": "Grizzlies vs Heat",
                "league": "NBA",
                "verdict": "MISSED CALL",
                "call": "Ruled No Foul",
                "description": "The shooter had already released the ball and the shot attempt was complete. The defense had gained control of the ball — contact occurred unnecessarily.",
                "impact": "-1.32",
                "time_ago": "34m ago",
            },
            {
                "id": "2",
                "teams": "Bulldogs vs Auburn Tigers",
                "league": "NCAAF",
                "verdict": "CORRECT CALL",
                "call": "Ruled Fumble",
                "description": "As the ball carrier approached the goal line, multiple defenders made contact attempting to halt his progress. The ball was clearly loose before crossing the plane.",
                "impact": "+2.1",
                "time_ago": "1h ago",
            },
            {
                "id": "3",
                "teams": "Lakers vs Celtics",
                "league": "NBA",
                "verdict": "MISSED CALL",
                "call": "No Call — Offensive Foul",
                "description": "Clear offensive foul missed by officials. The offensive player led with his shoulder into a set defender — textbook charge that went uncalled.",
                "impact": "-0.87",
                "time_ago": "2h ago",
            },
            {
                "id": "4",
                "teams": "Chiefs vs Ravens",
                "league": "NFL",
                "verdict": "MISSED CALL",
                "call": "Pass Interference Not Called",
                "description": "Defender made contact with the receiver well before the ball arrived, clearly affecting the play. Should have been an automatic first down.",
                "impact": "-3.2",
                "time_ago": "3h ago",
            },
            {
                "id": "5",
                "teams": "Penguins vs Rangers",
                "league": "NHL",
                "verdict": "CORRECT CALL",
                "call": "Goal Disallowed — Goalie Interference",
                "description": "Player made contact with the goalie in the crease prior to the puck crossing the line. Correct call under NHL Rule 69.",
                "impact": "+1.5",
                "time_ago": "4h ago",
            },
        ],
        "leaderboard": [
            {"rank": 1, "username": "Referee4", "calls_corrected": 8},
            {"rank": 2, "username": "Paulb", "calls_corrected": 7},
            {"rank": 3, "username": "bob940", "calls_corrected": 6},
            {"rank": 4, "username": "SportsFan22", "calls_corrected": 5},
            {"rank": 5, "username": "RefWatcher", "calls_corrected": 4},
        ],
    }
