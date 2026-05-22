"""One-shot Spurs watcher for GitHub Actions. Stateless.

Checks for Spurs matches that finished within the last 35 minutes
(30-min cron + 5-min buffer). No DB needed — the time window prevents
duplicate alerts across runs.
"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from src import formatting
from src.config import SPURS_TEAM_ID
from src.notifiers.fanout import Fanout
from src.sources.football_data import FootballDataClient

WINDOW = timedelta(minutes=35)


def _parse_iso(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _did_spurs_lose(match: dict) -> bool:
    if match.get("status") != "FINISHED":
        return False
    home_id = match.get("home_team_id")
    away_id = match.get("away_team_id")
    score_home = match.get("score_home")
    score_away = match.get("score_away")
    if score_home is None or score_away is None:
        return False
    if home_id == SPURS_TEAM_ID:
        return score_home < score_away
    if away_id == SPURS_TEAM_ID:
        return score_away < score_home
    return False


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_spurs_once")
    client = FootballDataClient()
    try:
        finished = await client.get_team_matches(status="FINISHED", team_id=SPURS_TEAM_ID)
    finally:
        await client.close()

    cutoff = datetime.now(timezone.utc) - WINDOW
    losses = [
        m for m in finished
        if _did_spurs_lose(m) and _parse_iso(m["utc_date"]) >= cutoff
    ]

    log.info("Found %d Spurs loss(es) in last %s", len(losses), WINDOW)
    if not losses:
        return

    fanout = Fanout.default()
    try:
        for match in losses:
            await fanout.send(formatting.format_spurs_loss(match))
        log.info("Sent %d Spurs loss alert(s)", len(losses))
    finally:
        await fanout.close()


if __name__ == "__main__":
    asyncio.run(main())
