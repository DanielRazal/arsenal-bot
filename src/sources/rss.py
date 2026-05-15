import asyncio
import logging
from typing import Iterable

import feedparser
import httpx

log = logging.getLogger(__name__)

USER_AGENT = "ArsenalBot/1.0 (+https://github.com/personal-use)"


async def fetch_feed(url: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            content = resp.content
    except httpx.HTTPError:
        log.warning("Failed to fetch feed: %s", url, exc_info=True)
        return []

    parsed = await asyncio.to_thread(feedparser.parse, content)
    return [
        {
            "link": entry.get("link", ""),
            "title": entry.get("title", ""),
            "summary": entry.get("summary", "") or entry.get("description", ""),
            "published": entry.get("published", "") or entry.get("updated", ""),
        }
        for entry in parsed.entries
        if entry.get("link")
    ]


async def fetch_all(feeds: Iterable[dict]) -> list[dict]:
    tasks = [fetch_feed(f["url"]) for f in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for feed_meta, items in zip(feeds, results):
        if isinstance(items, Exception):
            log.warning("Feed %s errored: %s", feed_meta["source"], items)
            continue
        for item in items:
            out.append({**item, "source": feed_meta["source"], "arsenal_only": feed_meta["arsenal_only"]})
    return out
