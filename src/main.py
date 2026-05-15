import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import db, formatting
from .config import LOG_LEVEL, TIMEZONE
from .llm.client import LLMClient
from .llm.match_summary import summarize_match
from .notifiers.fanout import Fanout
from .workers import match_watcher, morning_digest, news_poller


def _configure_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("arsenal-bot")
    db.init_db()

    fanout = Fanout.default()
    llm = LLMClient()

    async def on_event(event: dict) -> None:
        if event["type"] == "goal":
            await fanout.send(formatting.format_goal(event))

    async def on_prematch(match: dict) -> None:
        await fanout.send(formatting.format_prematch(match))

    async def on_finished(match: dict) -> None:
        summary_text = await summarize_match(llm, match)
        await fanout.send(formatting.format_match_finished(match, summary_text))

    async def on_new_article(article: dict) -> None:
        await fanout.send(formatting.format_news_item(article))

    async def on_digest(text: str, count: int) -> None:
        await fanout.send(formatting.format_morning_digest(text, count))

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
    morning_digest.schedule(scheduler, llm, on_digest)
    scheduler.start()

    log.info("Arsenal bot starting…")
    try:
        await asyncio.gather(
            match_watcher.run(on_event, on_prematch, on_finished, stop_event=stop_event),
            news_poller.run(on_new_article, stop_event=stop_event),
            stop_event.wait(),
        )
    finally:
        log.info("Shutting down…")
        scheduler.shutdown(wait=False)
        await llm.close()
        await fanout.close()


if __name__ == "__main__":
    asyncio.run(main())
