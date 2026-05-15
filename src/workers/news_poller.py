import asyncio
import logging

from .. import db
from ..sources.feeds import FEEDS, matches_arsenal
from ..sources.rss import fetch_all

log = logging.getLogger(__name__)

POLL_SECONDS = 15 * 60


async def run(on_new_article, *, stop_event: asyncio.Event | None = None) -> None:
    log.info("news_poller started")
    while not (stop_event and stop_event.is_set()):
        try:
            items = await fetch_all(FEEDS)
            new_count = 0
            for item in items:
                is_relevant = item["arsenal_only"] or matches_arsenal(
                    f"{item.get('title', '')} {item.get('summary', '')}"
                )
                if not is_relevant:
                    continue
                inserted = db.insert_article_if_new(
                    link=item["link"],
                    source=item["source"],
                    title=item["title"],
                    summary=item.get("summary", ""),
                    published_at=item.get("published", ""),
                )
                if inserted:
                    new_count += 1
                    await on_new_article(item)
                    db.mark_article_sent(item["link"])
            if new_count:
                log.info("news_poller: %d new article(s) sent", new_count)
        except Exception:
            log.exception("news_poller iteration failed; backing off")
        await asyncio.sleep(POLL_SECONDS)
    log.info("news_poller stopped")
