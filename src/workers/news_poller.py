import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .. import db
from ..sources.dedup import find_similar
from ..sources.feeds import (
    FEEDS,
    is_clickbait,
    is_mocking_content,
    is_women_content,
    matches_arsenal,
)
from ..sources.rss import fetch_all

log = logging.getLogger(__name__)

POLL_SECONDS = 15 * 60
FRESHNESS_WINDOW = timedelta(hours=24)


def _is_fresh(published_dt: datetime | None) -> bool:
    """Articles missing a timestamp or older than 24h are stored but not sent."""
    if published_dt is None:
        return False
    return datetime.now(timezone.utc) - published_dt <= FRESHNESS_WINDOW


async def run(on_new_article, *, stop_event: asyncio.Event | None = None) -> None:
    log.info("news_poller started")
    while not (stop_event and stop_event.is_set()):
        try:
            items = await fetch_all(FEEDS)
            # Pre-load recently sent titles so we can dedup cross-source within iteration too.
            recent_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            sent_titles = db.recent_sent_titles(recent_cutoff)
            new_count = 0
            seeded_count = 0
            clickbait_count = 0
            women_skipped = 0
            mocking_skipped = 0
            dup_skipped = 0
            for item in items:
                full_text = f"{item.get('title', '')} {item.get('summary', '')}"
                is_relevant = item["arsenal_only"] or matches_arsenal(full_text)
                if not is_relevant:
                    continue
                if is_women_content(full_text):
                    women_skipped += 1
                    continue
                if is_mocking_content(full_text):
                    mocking_skipped += 1
                    continue
                inserted = db.insert_article_if_new(
                    link=item["link"],
                    source=item["source"],
                    title=item["title"],
                    summary=item.get("summary", ""),
                    published_at=item.get("published", ""),
                )
                if not inserted:
                    continue
                if not _is_fresh(item.get("published_dt")):
                    seeded_count += 1
                    continue
                if is_clickbait(item.get("title", "")):
                    clickbait_count += 1
                    continue
                title = item.get("title", "")
                duplicate_of = find_similar(title, sent_titles)
                if duplicate_of:
                    dup_skipped += 1
                    log.debug("Skipping near-duplicate of %r: %r", duplicate_of, title)
                    continue
                new_count += 1
                await on_new_article(item)
                db.mark_article_sent(item["link"])
                sent_titles.append(title)
            if new_count:
                log.info("news_poller: %d new article(s) sent", new_count)
            if seeded_count:
                log.info("news_poller: %d older article(s) seeded silently", seeded_count)
            if clickbait_count:
                log.info("news_poller: %d clickbait article(s) deferred to digest", clickbait_count)
            if women_skipped:
                log.info("news_poller: %d women's-team article(s) filtered out", women_skipped)
            if mocking_skipped:
                log.info("news_poller: %d mocking/banter article(s) filtered out", mocking_skipped)
            if dup_skipped:
                log.info("news_poller: %d cross-source duplicate(s) skipped", dup_skipped)
        except Exception:
            log.exception("news_poller iteration failed; backing off")
        await asyncio.sleep(POLL_SECONDS)
    log.info("news_poller stopped")
