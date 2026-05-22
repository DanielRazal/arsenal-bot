"""One-shot news poll for GitHub Actions.

Stateless: uses a tight freshness window matched to the workflow cron
schedule (every 15 min). Articles published outside the window are
ignored, which avoids cross-run duplicates without needing a shared DB.
"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from src import formatting
from src.notifiers.fanout import Fanout
from src.sources.dedup import find_similar
from src.sources.feeds import (
    FEEDS,
    is_clickbait,
    is_confirmed_transfer,
    is_injury_news,
    is_mocking_content,
    is_women_content,
    matches_arsenal,
)
from src.sources.rss import fetch_all

# Cron runs every 15 min; allow 3 min buffer for cron drift.
FRESHNESS = timedelta(minutes=18)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_news_once")
    items = await fetch_all(FEEDS)
    cutoff = datetime.now(timezone.utc) - FRESHNESS

    relevant: list[dict] = []
    seen_links: set[str] = set()
    accepted_titles: list[str] = []
    for item in items:
        if item.get("link") in seen_links:
            continue
        full_text = f"{item.get('title', '')} {item.get('summary', '')}"
        is_relevant = item["arsenal_only"] or matches_arsenal(full_text)
        if not is_relevant:
            continue
        if is_women_content(full_text):
            continue
        if is_mocking_content(full_text):
            continue
        published = item.get("published_dt")
        if published is None or published < cutoff:
            continue
        title = item.get("title", "")
        full_text = f"{title} {item.get('summary', '')}"
        breaking = is_confirmed_transfer(full_text) or is_injury_news(full_text)
        if not breaking and is_clickbait(title):
            continue
        if find_similar(title, accepted_titles):
            continue
        seen_links.add(item["link"])
        accepted_titles.append(title)
        relevant.append({**item, "breaking": breaking})

    log.info("Found %d fresh article(s) within %s window", len(relevant), FRESHNESS)
    if not relevant:
        return

    fanout = Fanout.default()
    try:
        for item in relevant:
            if item.get("breaking"):
                full_text = f"{item.get('title', '')} {item.get('summary', '')}"
                if is_confirmed_transfer(full_text):
                    msg = formatting.format_transfer_alert(item)
                else:
                    msg = formatting.format_injury_alert(item)
            else:
                msg = formatting.format_news_item(item)
            await fanout.send(msg)
        log.info("Pushed %d article(s) to Telegram + Discord", len(relevant))
    finally:
        await fanout.close()


if __name__ == "__main__":
    asyncio.run(main())
