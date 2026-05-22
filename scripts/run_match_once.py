"""One-shot Arsenal match watcher for GitHub Actions.

State (sent event IDs, prematch/halftime/summary flags) is persisted
between runs via .match_state.json, which the workflow caches using
actions/cache with a rolling restore-key pattern.
"""
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src import formatting
from src.config import ARSENAL_TEAM_ID
from src.llm.client import LLMClient
from src.llm.match_summary import summarize_match
from src.notifiers.fanout import Fanout
from src.sources.football_data import FootballDataClient

STATE_FILE = Path(".match_state.json")
RED_CARD_TYPES = {"RED_CARD", "YELLOW_RED_CARD", "RED"}


def _parse_iso(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"sent_events": [], "prematch_sent": [], "halftime_sent": [], "summary_sent": []}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_match_once")

    state = _load_state()
    sent_events: set[str] = set(state.get("sent_events", []))
    prematch_sent: set[int] = set(state.get("prematch_sent", []))
    halftime_sent: set[int] = set(state.get("halftime_sent", []))
    summary_sent: set[int] = set(state.get("summary_sent", []))
    dirty = False

    client = FootballDataClient()
    fanout = Fanout.default()
    llm = LLMClient()

    try:
        # Check for a live match (IN_PLAY or PAUSED)
        live = await client.get_team_matches(status="IN_PLAY")
        if not live:
            live = await client.get_team_matches(status="PAUSED")

        if live:
            match = live[0]
            raw = match.get("raw", {})
            log.info("Live: %s vs %s [%s]", match["home_team"], match["away_team"], match["status"])

            for goal in raw.get("goals", []) or []:
                event_id = f"goal-{goal.get('minute')}-{(goal.get('scorer') or {}).get('id', '?')}"
                if event_id in sent_events:
                    continue
                await fanout.send(formatting.format_goal({
                    "type": "goal",
                    "match": match,
                    "minute": goal.get("minute"),
                    "scorer": (goal.get("scorer") or {}).get("name", "Unknown"),
                    "team": (goal.get("team") or {}).get("name", ""),
                    "is_arsenal": (goal.get("team") or {}).get("id") == ARSENAL_TEAM_ID,
                }))
                sent_events.add(event_id)
                dirty = True
                log.info("Sent goal %s", event_id)

            for booking in raw.get("bookings", []) or []:
                card_type = (booking.get("card") or "").upper()
                if card_type not in RED_CARD_TYPES:
                    continue
                player_id = (booking.get("player") or {}).get("id", "?")
                event_id = f"red-{booking.get('minute')}-{player_id}"
                if event_id in sent_events:
                    continue
                await fanout.send(formatting.format_red_card({
                    "type": "red_card",
                    "match": match,
                    "minute": booking.get("minute"),
                    "player": (booking.get("player") or {}).get("name", "Unknown"),
                    "team": (booking.get("team") or {}).get("name", ""),
                    "is_arsenal": (booking.get("team") or {}).get("id") == ARSENAL_TEAM_ID,
                    "second_yellow": card_type == "YELLOW_RED_CARD",
                }))
                sent_events.add(event_id)
                dirty = True
                log.info("Sent red card %s", event_id)

            if match["status"] == "PAUSED" and match["id"] not in halftime_sent:
                await fanout.send(formatting.format_halftime(match))
                halftime_sent.add(match["id"])
                dirty = True
                log.info("Sent halftime alert for match %s", match["id"])

        else:
            # No live match — check prematch window
            scheduled = await client.get_team_matches(status="SCHEDULED")
            if not scheduled:
                scheduled = await client.get_team_matches(status="TIMED")
            if scheduled:
                scheduled.sort(key=lambda m: m["utc_date"])
                upcoming = scheduled[0]
                minutes_left = (_parse_iso(upcoming["utc_date"]) - datetime.now(timezone.utc)).total_seconds() / 60
                if 0 < minutes_left <= 30 and upcoming["id"] not in prematch_sent:
                    await fanout.send(formatting.format_prematch(upcoming))
                    prematch_sent.add(upcoming["id"])
                    dirty = True
                    log.info("Sent prematch alert for match %s", upcoming["id"])

            # Check for a recently finished match that needs a summary
            finished = await client.get_team_matches(status="FINISHED")
            if finished:
                finished.sort(key=lambda m: m["utc_date"], reverse=True)
                latest = finished[0]
                age = datetime.now(timezone.utc) - _parse_iso(latest["utc_date"])
                if age < timedelta(hours=4) and latest["id"] not in summary_sent:
                    summary_text = await summarize_match(llm, latest)
                    await fanout.send(formatting.format_match_finished(latest, summary_text))
                    summary_sent.add(latest["id"])
                    dirty = True
                    log.info("Sent match summary for match %s", latest["id"])

    finally:
        await client.close()
        await llm.close()
        await fanout.close()

    if dirty:
        _save_state({
            "sent_events": list(sent_events),
            "prematch_sent": list(prematch_sent),
            "halftime_sent": list(halftime_sent),
            "summary_sent": list(summary_sent),
        })
        log.info("State saved")
    else:
        log.info("No new events")


if __name__ == "__main__":
    asyncio.run(main())
