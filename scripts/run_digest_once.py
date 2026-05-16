"""One-shot morning digest for GitHub Actions.

Pulls every relevant article from the last 24h across the RSS feeds,
deduplicates by link, and asks the LLM for a Hebrew morning digest.
Stateless — runs cleanly on every cron tick without needing a DB.
"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from src import formatting
from src.llm.article_digest import make_digest
from src.llm.client import LLMClient
from src.notifiers.fanout import Fanout
from src.sources.feeds import (
    FEEDS,
    is_mocking_content,
    is_women_content,
    matches_arsenal,
)
from src.sources.rss import fetch_all

LOOKBACK = timedelta(hours=24)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_digest_once")
    items = await fetch_all(FEEDS)
    cutoff = datetime.now(timezone.utc) - LOOKBACK

    articles: list[dict] = []
    seen_links: set[str] = set()
    for item in items:
        link = item.get("link")
        if not link or link in seen_links:
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
        seen_links.add(link)
        articles.append({
            "link": link,
            "source": item.get("source", ""),
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
        })

    log.info("Building digest from %d article(s) in last 24h", len(articles))
    fanout = Fanout.default()
    llm = LLMClient()
    try:
        digest_text = await make_digest(llm, articles)
        await fanout.send(formatting.format_morning_digest(digest_text, len(articles)))
        log.info("Digest sent")
    finally:
        await llm.close()
        await fanout.close()


if __name__ == "__main__":
    asyncio.run(main())
