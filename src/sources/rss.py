import asyncio
import logging
from datetime import datetime, timezone
from time import struct_time
from typing import Iterable

import feedparser
import httpx

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "ArsenalBot/1.0 (+https://github.com/DanielRazal/arsenal-bot)"
)


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
            "published_dt": _to_datetime(
                entry.get("published_parsed") or entry.get("updated_parsed")
            ),
        }
        for entry in parsed.entries
        if entry.get("link")
    ]


def _to_datetime(parsed_time: struct_time | None) -> datetime | None:
    if parsed_time is None:
        return None
    try:
        return datetime(*parsed_time[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


async def fetch_all(feeds: Iterable[dict]) -> list[dict]:
    tasks = [fetch_feed(f["url"]) for f in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    counts = []
    for feed_meta, items in zip(feeds, results):
        if isinstance(items, Exception):
            log.warning("Feed %s errored: %s", feed_meta["source"], items)
            counts.append(f"{feed_meta['source']}=ERR")
            continue
        counts.append(f"{feed_meta['source']}={len(items)}")
        for item in items:
            out.append({
                **item,
                "source": feed_meta["source"],
                "arsenal_only": feed_meta["arsenal_only"],
                "title_match_only": feed_meta.get("title_match_only", False),
                "lang": feed_meta.get("lang", "he"),
            })
    log.info("fetch_all per-feed item counts: %s", " · ".join(counts))
    return out
