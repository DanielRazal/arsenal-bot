import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .. import db
from ..llm.client import LLMClient
from ..llm.news_dedup import is_duplicate_story
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


DEAD_FEED_POLLS = 4  # consecutive empty polls (~1h at 15-min cadence) before alerting


async def run(
    on_new_article,
    *,
    stop_event: asyncio.Event | None = None,
    llm: LLMClient | None = None,
    on_alert=None,
) -> None:
    log.info("news_poller started")
    zero_streak: dict[str, int] = {}
    dead_alerted: set[str] = set()
    # On a host with an ephemeral filesystem (free Render), the SQLite dedup
    # state is wiped on every restart/redeploy. Without priming, the first poll
    # after a restart re-announces every article published in the last 24h that
    # was already sent before the restart. So on the FIRST iteration we seed the
    # current feed contents silently and send nothing; only articles that appear
    # in later iterations (i.e. after startup) are pushed.
    first_run = True
    while not (stop_event and stop_event.is_set()):
        try:
            items = await fetch_all(FEEDS)
            # Dead-feed watch: a feed that returns 0 items for several polls in a
            # row is broken (e.g. blocked IP). Alert once, and once on recovery.
            if on_alert is not None:
                per_source = {f["source"]: 0 for f in FEEDS}
                for it in items:
                    per_source[it["source"]] = per_source.get(it["source"], 0) + 1
                for src, n in per_source.items():
                    if n == 0:
                        zero_streak[src] = zero_streak.get(src, 0) + 1
                        if zero_streak[src] == DEAD_FEED_POLLS and src not in dead_alerted:
                            dead_alerted.add(src)
                            await on_alert(f"⚠️ מקור החדשות \"{src}\" לא מחזיר פריטים כבר זמן מה — ייתכן שהוא נחסם או נפל.")
                    else:
                        if src in dead_alerted:
                            await on_alert(f"✅ מקור החדשות \"{src}\" חזר לעבוד.")
                        zero_streak[src] = 0
                        dead_alerted.discard(src)
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
                title = item.get("title", "")
                full_text = f"{title} {item.get('summary', '')}"
                if item["arsenal_only"]:
                    is_relevant = True
                elif item.get("title_match_only"):
                    # Broad feed (e.g. Israeli sport): require the keyword in the
                    # title to avoid passing-mention false positives.
                    is_relevant = matches_arsenal(title)
                else:
                    is_relevant = matches_arsenal(full_text)
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
                if first_run:
                    # Pre-existing article: record it as already-sent so it is
                    # never announced, and so it counts toward cross-source dedup.
                    db.mark_article_sent(item["link"])
                    seeded_count += 1
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
                # Second pass: LLM catches paraphrased/cross-language duplicates
                # that share too few words for the token check above.
                if llm is not None and await is_duplicate_story(llm, title, sent_titles):
                    dup_skipped += 1
                    log.info("Semantic dedup skipped near-duplicate: %r", title)
                    continue
                new_count += 1
                await on_new_article(item)
                db.mark_article_sent(item["link"])
                sent_titles.append(title)
            if new_count:
                log.info("news_poller: %d new article(s) sent", new_count)
            if seeded_count:
                if first_run:
                    log.info("news_poller: primed %d existing article(s) silently on startup", seeded_count)
                else:
                    log.info("news_poller: %d older article(s) seeded silently", seeded_count)
            if clickbait_count:
                log.info("news_poller: %d clickbait article(s) deferred to digest", clickbait_count)
            if women_skipped:
                log.info("news_poller: %d women's-team article(s) filtered out", women_skipped)
            if mocking_skipped:
                log.info("news_poller: %d mocking/banter article(s) filtered out", mocking_skipped)
            if dup_skipped:
                log.info("news_poller: %d cross-source duplicate(s) skipped", dup_skipped)
            # Only flip after a fully successful pass, so a failed first fetch
            # retries the silent priming instead of going live with an empty DB.
            first_run = False
        except Exception:
            log.exception("news_poller iteration failed; backing off")
        await asyncio.sleep(POLL_SECONDS)
    log.info("news_poller stopped")
