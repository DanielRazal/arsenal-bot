"""Standings change detector — scheduled worker version.

Ported from scripts/run_standings_alert_once.py (GitHub Actions one-shot) so it
runs inside the always-on process. Every few hours it compares Arsenal's league
position to the previous check and alerts on meaningful crossings (1st place,
top-4 boundary).

State (the previous position) is kept in memory rather than on disk: on a fresh
restart there is no "previous", so the first check simply records the current
position without alerting — which avoids a bogus alert after every deploy on an
ephemeral host.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import formatting
from ..config import ARSENAL_TEAM_ID, TIMEZONE
from ..notifiers.fanout import Fanout
from ..sources.football_data import FootballDataClient

log = logging.getLogger(__name__)

# Match the old workflow cadence: every 6 hours (standings settle after matches).
CHECK_HOURS = "*/6"


def _detect_event(prev: int | None, curr: int) -> str | None:
    if prev is None:
        return None
    if curr == 1 and prev != 1:
        return "first"
    if prev == 1 and curr != 1:
        return "dropped_first"
    if curr <= 4 and prev > 4:
        return "top4_in"
    if curr > 4 and prev <= 4:
        return "top4_out"
    return None


async def _check_standings(client: FootballDataClient, fanout: Fanout, state: dict) -> None:
    rows = await client.get_standings("PL")
    arsenal_row = next((r for r in rows if r.get("team_id") == ARSENAL_TEAM_ID), None)
    if not arsenal_row:
        log.warning("Arsenal not found in standings")
        return

    curr_position: int = arsenal_row["position"]
    prev_position: int | None = state.get("position")
    log.info("standings_alert: position %s (was %s)", curr_position, prev_position)
    state["position"] = curr_position

    event = _detect_event(prev_position, curr_position)
    if event is None:
        return
    await fanout.send(formatting.format_standings_alert(event, arsenal_row, prev_position))
    log.info("Sent standings alert: %s", event)


def schedule(scheduler: AsyncIOScheduler, client: FootballDataClient, fanout: Fanout) -> None:
    state: dict = {"position": None}
    trigger = CronTrigger(hour=CHECK_HOURS, minute=0, timezone=TIMEZONE)
    scheduler.add_job(
        _check_standings,
        trigger=trigger,
        args=[client, fanout, state],
        id="standings_alert",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    log.info("standings_alert scheduled every 6 hours (%s)", TIMEZONE)
