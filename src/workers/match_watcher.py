import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .. import db
from ..config import ARSENAL_TEAM_ID
from ..sources.football_data import FootballDataClient

log = logging.getLogger(__name__)

IDLE_POLL_SECONDS = 3600
PREMATCH_POLL_SECONDS = 60
LIVE_POLL_SECONDS = 45
PREMATCH_WINDOW_MINUTES = 30


def _parse_iso(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


async def _find_next_match(client: FootballDataClient) -> dict | None:
    matches = await client.get_team_matches(status="SCHEDULED")
    if not matches:
        matches = await client.get_team_matches(status="TIMED")
    if not matches:
        return None
    matches.sort(key=lambda m: m["utc_date"])
    return matches[0]


async def _check_live_match(client: FootballDataClient) -> dict | None:
    live = await client.get_team_matches(status="IN_PLAY")
    if live:
        return live[0]
    paused = await client.get_team_matches(status="PAUSED")
    return paused[0] if paused else None


async def _handle_finished_match(match: dict, on_finished) -> None:
    db.upsert_match(match)
    if db.match_needs_summary(match["id"]):
        log.info("Match %s finished — triggering summary", match["id"])
        await on_finished(match)
        db.mark_summary_sent(match["id"])


RED_CARD_TYPES = {"RED_CARD", "YELLOW_RED_CARD", "RED"}


async def _handle_live_match(match: dict, on_event) -> None:
    db.upsert_match(match)
    raw = match.get("raw", {})
    goals = raw.get("goals", []) or []
    for goal in goals:
        event_id = f"goal-{goal.get('minute')}-{(goal.get('scorer') or {}).get('id', '?')}"
        if db.event_already_sent(match["id"], event_id):
            continue
        scorer_name = (goal.get("scorer") or {}).get("name", "Unknown")
        team_name = (goal.get("team") or {}).get("name", "")
        is_arsenal = (goal.get("team") or {}).get("id") == ARSENAL_TEAM_ID
        await on_event({
            "type": "goal",
            "match": match,
            "minute": goal.get("minute"),
            "scorer": scorer_name,
            "team": team_name,
            "is_arsenal": is_arsenal,
        })
        db.mark_event_sent(match["id"], event_id)

    bookings = raw.get("bookings", []) or []
    for booking in bookings:
        card_type = (booking.get("card") or "").upper()
        if card_type not in RED_CARD_TYPES:
            continue
        player_id = (booking.get("player") or {}).get("id", "?")
        event_id = f"red-{booking.get('minute')}-{player_id}"
        if db.event_already_sent(match["id"], event_id):
            continue
        player_name = (booking.get("player") or {}).get("name", "Unknown")
        team_name = (booking.get("team") or {}).get("name", "")
        is_arsenal = (booking.get("team") or {}).get("id") == ARSENAL_TEAM_ID
        await on_event({
            "type": "red_card",
            "match": match,
            "minute": booking.get("minute"),
            "player": player_name,
            "team": team_name,
            "is_arsenal": is_arsenal,
            "second_yellow": card_type == "YELLOW_RED_CARD",
        })
        db.mark_event_sent(match["id"], event_id)


async def _handle_prematch(match: dict, on_prematch) -> None:
    db.upsert_match(match)
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT prematch_alert_sent FROM matches WHERE id=?", (match["id"],)
        ).fetchone()
    if row and row["prematch_alert_sent"] == 1:
        return
    log.info("Sending prematch alert for match %s", match["id"])
    await on_prematch(match)
    db.mark_prematch_sent(match["id"])


async def _handle_halftime(match: dict, on_halftime) -> None:
    if db.halftime_already_sent(match["id"]):
        return
    log.info("Sending halftime alert for match %s", match["id"])
    await on_halftime(match)
    db.mark_halftime_sent(match["id"])


async def run(
    on_event,
    on_prematch,
    on_finished,
    on_halftime,
    *,
    stop_event: asyncio.Event | None = None,
) -> None:
    client = FootballDataClient()
    log.info("match_watcher started")
    try:
        while not (stop_event and stop_event.is_set()):
            try:
                live = await _check_live_match(client)
                if live:
                    await _handle_live_match(live, on_event)
                    if live["status"] == "PAUSED":
                        await _handle_halftime(live, on_halftime)
                    if live["status"] == "FINISHED":
                        await _handle_finished_match(live, on_finished)
                    await asyncio.sleep(LIVE_POLL_SECONDS)
                    continue

                upcoming = await _find_next_match(client)
                if upcoming:
                    kickoff = _parse_iso(upcoming["utc_date"])
                    minutes_to_kickoff = (kickoff - datetime.now(timezone.utc)).total_seconds() / 60
                    if 0 < minutes_to_kickoff <= PREMATCH_WINDOW_MINUTES:
                        await _handle_prematch(upcoming, on_prematch)
                        await asyncio.sleep(PREMATCH_POLL_SECONDS)
                        continue

                # Also check for very recently finished games that we missed
                recent = await client.get_team_matches(status="FINISHED")
                if recent:
                    recent.sort(key=lambda m: m["utc_date"], reverse=True)
                    latest = recent[0]
                    finished_at = _parse_iso(latest["utc_date"])
                    if datetime.now(timezone.utc) - finished_at < timedelta(hours=4):
                        await _handle_finished_match(latest, on_finished)

                await asyncio.sleep(IDLE_POLL_SECONDS)
            except Exception:
                log.exception("match_watcher iteration failed; backing off 60s")
                await asyncio.sleep(60)
    finally:
        await client.close()
        log.info("match_watcher stopped")
