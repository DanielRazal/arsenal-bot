"""One-shot standings change detector for GitHub Actions.

Reads the previous Arsenal position from .standings_state.json (cached
between runs via actions/cache) and sends an alert if the position crossed
a meaningful threshold (1st place, top-4 boundary).
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

from src import formatting
from src.config import ARSENAL_TEAM_ID
from src.notifiers.fanout import Fanout
from src.sources.football_data import FootballDataClient

STATE_FILE = Path(".standings_state.json")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"position": None}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


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


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_standings_alert_once")

    state = _load_state()
    prev_position: int | None = state.get("position")

    client = FootballDataClient()
    try:
        rows = await client.get_standings("PL")
    finally:
        await client.close()

    arsenal_row = next((r for r in rows if r.get("team_id") == ARSENAL_TEAM_ID), None)
    if not arsenal_row:
        log.warning("Arsenal not found in standings")
        return

    curr_position: int = arsenal_row["position"]
    log.info("Arsenal: position %s (was %s)", curr_position, prev_position)

    _save_state({"position": curr_position})

    event = _detect_event(prev_position, curr_position)
    if event is None:
        log.info("No notable position change")
        return

    fanout = Fanout.default()
    try:
        await fanout.send(formatting.format_standings_alert(event, arsenal_row, prev_position))
        log.info("Sent standings alert: %s", event)
    finally:
        await fanout.close()


if __name__ == "__main__":
    asyncio.run(main())
