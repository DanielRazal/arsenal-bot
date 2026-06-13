import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import db, formatting
from .health import start_health_server
from .config import (
    ARSENAL_TEAM_ID,
    ENABLE_MORNING_DIGEST,
    ENABLE_NEWS_POLLER,
    ENABLE_STANDINGS_ALERT,
    ENABLE_WEEKLY_RECAP,
    LOG_LEVEL,
    TIMEZONE,
)
from .sources.espn import fetch_arsenal_squad
from .llm.client import LLMClient
from .llm.match_summary import summarize_match
from .llm.translate import translate_title
from .notifiers.fanout import Fanout
from .sources.football_data import FootballDataClient
from .workers import match_watcher, morning_digest, news_poller, spurs_watcher, standings_alert, weekly_recap


def _configure_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )
    # SECURITY: httpx logs every request line at INFO, which includes the full
    # URL — and the Telegram bot token is embedded in that URL (/bot<TOKEN>/…)
    # and the Discord webhook URL *is* a secret. Silence these libraries so
    # credentials never reach the logs (kept separately from the app's own
    # INFO logs, which carry no secrets).
    for noisy in ("httpx", "httpcore", "telegram", "telegram.ext", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("arsenal-bot")
    db.init_db()
    start_health_server()  # binds $PORT so Render accepts this as a Web Service

    fanout = Fanout.default()
    llm = LLMClient()
    fd_client = FootballDataClient()

    async def cmd_next(_args: str) -> str:
        try:
            matches = await fd_client.get_team_matches(status="SCHEDULED")
            if not matches:
                matches = await fd_client.get_team_matches(status="TIMED")
            matches.sort(key=lambda m: m["utc_date"])
            return formatting.format_next_matches(matches[:3])
        except Exception:
            log.exception("/next command failed")
            return "לא הצלחתי לשלוף את המשחקים כרגע, נסה שוב בעוד דקה."

    async def cmd_standings(_args: str) -> str:
        try:
            rows = await fd_client.get_standings("PL")
            return formatting.format_standings(rows)
        except Exception:
            log.exception("/standings command failed")
            return "לא הצלחתי לשלוף את הטבלה כרגע, נסה שוב בעוד דקה."

    async def cmd_last(_args: str) -> str:
        try:
            finished = await fd_client.get_team_matches(status="FINISHED")
            if not finished:
                return "לא מצאתי משחקים שהסתיימו לאחרונה."
            finished.sort(key=lambda m: m["utc_date"], reverse=True)
            match = finished[0]
            summary = await summarize_match(llm, match)
            return formatting.format_match_finished(match, summary)
        except Exception:
            log.exception("/last command failed")
            return "לא הצלחתי לשלוף את המשחק האחרון, נסה שוב."

    async def cmd_squad(_args: str) -> str:
        try:
            players = await fetch_arsenal_squad()
            return formatting.format_squad(players)
        except Exception:
            log.exception("/squad command failed")
            return "לא הצלחתי לשלוף את ההרכב כרגע."

    async def cmd_stats(_args: str) -> str:
        try:
            scorers = await fd_client.get_scorers()
            arsenal_scorers = [s for s in scorers if s["team_id"] == ARSENAL_TEAM_ID]
            return formatting.format_stats(arsenal_scorers)
        except Exception:
            log.exception("/stats command failed")
            return "לא הצלחתי לשלוף את הסטטיסטיקות כרגע."

    async def cmd_help(_args: str) -> str:
        return formatting.format_help()

    fanout.register_telegram_command("next", cmd_next)
    fanout.register_telegram_command("standings", cmd_standings)
    fanout.register_telegram_command("last", cmd_last)
    fanout.register_telegram_command("squad", cmd_squad)
    fanout.register_telegram_command("stats", cmd_stats)
    fanout.register_telegram_command("help", cmd_help)

    async def on_event(event: dict) -> None:
        if event["type"] == "goal":
            await fanout.send(formatting.format_goal(event))
        elif event["type"] == "red_card":
            await fanout.send(formatting.format_red_card(event))

    async def on_prematch(match: dict) -> None:
        await fanout.send(formatting.format_prematch(match))

    async def on_halftime(match: dict) -> None:
        await fanout.send(formatting.format_halftime(match))

    async def on_finished(match: dict) -> None:
        summary_text = await summarize_match(llm, match)
        await fanout.send(formatting.format_match_finished(match, summary_text))

    async def on_new_article(article: dict) -> None:
        # English-source articles are translated to Hebrew before sending so the
        # feed stays Hebrew. Failures fall back to the original inside translate_title.
        if article.get("lang") == "en":
            he_title = await translate_title(llm, article.get("title", ""))
            article = {**article, "title": he_title}
        await fanout.send(formatting.format_news_item(article))

    async def on_digest(text: str, count: int) -> None:
        await fanout.send(formatting.format_morning_digest(text, count))

    async def on_spurs_loss(match: dict) -> None:
        await fanout.send(formatting.format_spurs_loss(match))

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop(*_args) -> None:
        log.info("Stop requested")
        stop_event.set()

    for sig_name in ("SIGTERM", "SIGINT"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler — fall back to signal.signal
            signal.signal(sig, _request_stop)

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    if ENABLE_MORNING_DIGEST:
        morning_digest.schedule(scheduler, llm, on_digest)
    else:
        log.info("Morning digest disabled (handled by GitHub Actions)")
    if ENABLE_STANDINGS_ALERT:
        standings_alert.schedule(scheduler, fd_client, fanout)
    else:
        log.info("Standings alert disabled (handled by GitHub Actions)")
    if ENABLE_WEEKLY_RECAP:
        weekly_recap.schedule(scheduler, fd_client, llm, fanout)
    else:
        log.info("Weekly recap disabled (handled by GitHub Actions)")
    scheduler.start()

    log.info("Arsenal bot starting…")
    await fanout.start()
    tasks = [
        match_watcher.run(on_event, on_prematch, on_finished, on_halftime, stop_event=stop_event),
        spurs_watcher.run(on_spurs_loss, stop_event=stop_event),
        stop_event.wait(),
    ]
    if ENABLE_NEWS_POLLER:
        tasks.insert(1, news_poller.run(on_new_article, stop_event=stop_event))
    else:
        log.info("News poller disabled (handled by GitHub Actions)")
    try:
        await asyncio.gather(*tasks)
    finally:
        log.info("Shutting down…")
        scheduler.shutdown(wait=False)
        await fd_client.close()
        await llm.close()
        await fanout.close()


if __name__ == "__main__":
    asyncio.run(main())
