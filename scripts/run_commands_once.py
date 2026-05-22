"""One-shot Telegram command processor for GitHub Actions.

Fetches pending updates via getUpdates (offset-based), processes any
recognised commands, and replies. No persistent polling loop needed.
State (last seen update_id) is persisted between runs via
.commands_state.json cached by actions/cache.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx

from src import formatting
from src.config import ARSENAL_TEAM_ID, TELEGRAM_BOT_TOKEN
from src.llm.client import LLMClient
from src.llm.match_summary import summarize_match
from src.sources.football_data import FootballDataClient

STATE_FILE = Path(".commands_state.json")
TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
KNOWN_COMMANDS = {"last", "squad", "stats", "next", "standings"}

# Poll for this long before exiting. Cron fires every minute, so 55s gives
# continuous coverage even when GitHub delays the next trigger.
POLL_WINDOW = 55
POLL_INTERVAL = 2


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"offset": 0}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


def _parse_command(update: dict) -> tuple[str | None, int | None]:
    """Returns (command_name, chat_id) or (None, None)."""
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return None, None
    text = (msg.get("text") or "").strip()
    if not text.startswith("/"):
        return None, None
    cmd = text[1:].split(maxsplit=1)[0].split("@", 1)[0].lower()
    chat_id = (msg.get("chat") or {}).get("id")
    return cmd, chat_id


async def _reply(tg: httpx.AsyncClient, chat_id: int, text: str, log: logging.Logger) -> None:
    try:
        resp = await tg.post(
            f"{TG_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
    except Exception:
        log.exception("sendMessage failed for chat %s", chat_id)


async def _handle(cmd: str, fd: FootballDataClient, llm: LLMClient) -> str:
    if cmd == "last":
        finished = await fd.get_team_matches(status="FINISHED")
        if not finished:
            return "לא מצאתי משחקים שהסתיימו לאחרונה."
        finished.sort(key=lambda m: m["utc_date"], reverse=True)
        match = finished[0]
        summary = await summarize_match(llm, match)
        return formatting.format_match_finished(match, summary)
    if cmd == "squad":
        return formatting.format_squad(await fd.get_squad())
    if cmd == "stats":
        scorers = [s for s in await fd.get_scorers() if s["team_id"] == ARSENAL_TEAM_ID]
        return formatting.format_stats(scorers)
    if cmd == "next":
        matches = await fd.get_team_matches(status="SCHEDULED") or await fd.get_team_matches(status="TIMED")
        matches.sort(key=lambda m: m["utc_date"])
        return formatting.format_next_matches(matches[:3])
    if cmd == "standings":
        return formatting.format_standings(await fd.get_standings("PL"))
    return ""


async def _fetch_updates(tg: httpx.AsyncClient, offset: int) -> list[dict]:
    resp = await tg.get(
        f"{TG_API}/getUpdates",
        params={"offset": offset, "timeout": 0},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_commands_once")

    state = _load_state()
    offset: int = state.get("offset", 0)

    fd = FootballDataClient()
    llm = LLMClient()
    deadline = asyncio.get_event_loop().time() + POLL_WINDOW

    try:
        async with httpx.AsyncClient() as tg:
            while asyncio.get_event_loop().time() < deadline:
                try:
                    updates = await _fetch_updates(tg, offset)
                except Exception:
                    log.exception("getUpdates failed, retrying")
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                if not updates:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                # Advance offset immediately to avoid re-processing on error
                offset = max(u["update_id"] for u in updates) + 1
                _save_state({"offset": offset})
                log.info("Got %d update(s), offset now %d", len(updates), offset)

                for update in updates:
                    cmd, chat_id = _parse_command(update)
                    if not cmd or cmd not in KNOWN_COMMANDS or not chat_id:
                        continue
                    log.info("Handling /%s for chat %s", cmd, chat_id)
                    try:
                        reply_text = await _handle(cmd, fd, llm)
                    except Exception:
                        log.exception("Handler failed for /%s", cmd)
                        reply_text = "שגיאה פנימית, נסה שוב מאוחר יותר."
                    if reply_text:
                        await _reply(tg, chat_id, reply_text, log)
    finally:
        await fd.close()
        await llm.close()


if __name__ == "__main__":
    asyncio.run(main())
