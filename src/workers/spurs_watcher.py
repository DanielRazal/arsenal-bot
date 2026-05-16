"""Watches Tottenham matches and alerts when they lose. Pure joy."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .. import db
from ..config import SPURS_TEAM_ID
from ..sources.football_data import FootballDataClient

log = logging.getLogger(__name__)

# Spurs don't play that often, so we can be relaxed about polling.
POLL_SECONDS = 30 * 60
RECENT_HOURS = 6


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


async def run(on_spurs_loss, *, stop_event: asyncio.Event | None = None) -> None:
    """Long-running poll. on_spurs_loss(match) is fired once per defeat."""
    client = FootballDataClient()
    log.info("spurs_watcher started")
    try:
        while not (stop_event and stop_event.is_set()):
            try:
                finished = await client.get_team_matches(
                    status="FINISHED", team_id=SPURS_TEAM_ID
                )
                cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_HOURS)
                for match in finished:
                    when = _parse_iso(match["utc_date"])
                    if when < cutoff:
                        continue
                    if not _did_spurs_lose(match):
                        continue
                    event_key = f"spurs-loss-{match['id']}"
                    if db.event_already_sent(match["id"], event_key):
                        continue
                    log.info("Spurs lost match %s — sending schadenfreude", match["id"])
                    await on_spurs_loss(match)
                    db.mark_event_sent(match["id"], event_key)
            except Exception:
                log.exception("spurs_watcher iteration failed; backing off")
            await asyncio.sleep(POLL_SECONDS)
    finally:
        await client.close()
        log.info("spurs_watcher stopped")
