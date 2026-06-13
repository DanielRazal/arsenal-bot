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


def _goal_event_id(goal: dict) -> str:
    return f"goal-{goal.get('minute')}-{(goal.get('scorer') or {}).get('id', '?')}"


def _card_event_id(booking: dict) -> str:
    player_id = (booking.get("player") or {}).get("id", "?")
    return f"red-{booking.get('minute')}-{player_id}"


async def _handle_live_match(match: dict, on_event) -> None:
    db.upsert_match(match)
    raw = match.get("raw", {})
    goals = raw.get("goals", []) or []
    for goal in goals:
        event_id = _goal_event_id(goal)
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
        event_id = _card_event_id(booking)
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


async def prime_state(client: FootballDataClient) -> None:
    """Sync the DB to current reality on startup WITHOUT notifying.

    On a host with an ephemeral filesystem (e.g. a free Render Web Service)
    the SQLite state is wiped on every restart/deploy. Without this, a restart
    in the middle of a live match would re-announce every goal/card already on
    the scoreboard, and re-send the post-match summary. Here we record the
    current events as "already sent" so only genuinely new events fire after
    boot. The only cost is a real-time event landing in the ~1-minute restart
    window, which is rare.

    No-op (and silent) when the DB already knows about these events — i.e. on a
    host with persistent state, priming simply re-confirms what's there.
    """
    try:
        live = await _check_live_match(client)
        if live:
            db.upsert_match(live)
            raw = live.get("raw", {})
            for goal in raw.get("goals", []) or []:
                db.mark_event_sent(live["id"], _goal_event_id(goal))
            for booking in raw.get("bookings", []) or []:
                if (booking.get("card") or "").upper() in RED_CARD_TYPES:
                    db.mark_event_sent(live["id"], _card_event_id(booking))
            db.mark_prematch_sent(live["id"])
            if live["status"] in ("PAUSED", "FINISHED"):
                db.mark_halftime_sent(live["id"])
            log.info("Primed live match %s — existing events suppressed", live["id"])

        # Suppress re-summarizing a game that already finished before boot.
        recent = await client.get_team_matches(status="FINISHED")
        if recent:
            recent.sort(key=lambda m: m["utc_date"], reverse=True)
            latest = recent[0]
            finished_at = _parse_iso(latest["utc_date"])
            if datetime.now(timezone.utc) - finished_at < timedelta(hours=4):
                db.upsert_match(latest)
                db.mark_summary_sent(latest["id"])
                db.mark_prematch_sent(latest["id"])
                db.mark_halftime_sent(latest["id"])
                log.info("Primed recently-finished match %s — summary suppressed", latest["id"])
    except Exception:
        log.exception("prime_state failed; continuing without priming")


FAIL_STREAK_ALERT = 5  # consecutive failed iterations (~5 min) before alerting


async def run(
    on_event,
    on_prematch,
    on_finished,
    on_halftime,
    *,
    stop_event: asyncio.Event | None = None,
    on_alert=None,
) -> None:
    client = FootballDataClient()
    log.info("match_watcher started")
    await prime_state(client)
    fail_streak = 0
    alerted_down = False
    try:
        while not (stop_event and stop_event.is_set()):
            try:
                live = await _check_live_match(client)
                # The API responded — clear any failure streak / down-alert.
                if alerted_down and on_alert is not None:
                    await on_alert("✅ ניטור המשחקים חזר לעבוד (football-data שב לתקינות).")
                alerted_down = False
                fail_streak = 0
                if live:
                    await _handle_live_match(live, on_event)
                    if live["status"] == "PAUSED":
                        await _handle_halftime(live, on_halftime)
                    if live["status"] == "FINISHED":
                        await _handle_finished_match(live, on_finished)
                    await asyncio.sleep(LIVE_POLL_SECONDS)
                    continue

                upcoming = await _find_next_match(client)
                minutes_to_kickoff = None
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

                # Kickoff-aware idle: sleep only until the next match's pre-match
                # window opens, so the long idle poll can never overshoot a kickoff
                # and miss the start (and early goals). Full idle when nothing soon.
                idle = IDLE_POLL_SECONDS
                if minutes_to_kickoff is not None and minutes_to_kickoff > PREMATCH_WINDOW_MINUTES:
                    secs_to_window = (minutes_to_kickoff - PREMATCH_WINDOW_MINUTES) * 60
                    idle = min(IDLE_POLL_SECONDS, max(PREMATCH_POLL_SECONDS, secs_to_window))
                await asyncio.sleep(idle)
            except Exception:
                log.exception("match_watcher iteration failed; backing off 60s")
                fail_streak += 1
                if fail_streak >= FAIL_STREAK_ALERT and not alerted_down and on_alert is not None:
                    alerted_down = True
                    await on_alert("⚠️ ניטור המשחקים נכשל שוב ושוב — ייתכן ש-football-data למטה. ייתכן פספוס התראות חיות.")
                await asyncio.sleep(60)
    finally:
        await client.close()
        log.info("match_watcher stopped")
