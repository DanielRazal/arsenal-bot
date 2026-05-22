"""Weekly Arsenal recap for GitHub Actions. Runs every Friday."""
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from src import formatting
from src.config import ARSENAL_TEAM_ID
from src.llm.client import LLMClient
from src.llm.weekly_recap import make_weekly_recap
from src.notifiers.fanout import Fanout
from src.sources.feeds import FEEDS, is_mocking_content, is_women_content, matches_arsenal
from src.sources.football_data import FootballDataClient
from src.sources.rss import fetch_all

LOOKBACK = timedelta(days=7)


def _parse_iso(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_weekly_once")

    cutoff = datetime.now(timezone.utc) - LOOKBACK
    client = FootballDataClient()
    llm = LLMClient()
    fanout = Fanout.default()

    try:
        finished = await client.get_team_matches(status="FINISHED")
        recent_matches = sorted(
            [m for m in finished if _parse_iso(m["utc_date"]) >= cutoff],
            key=lambda m: m["utc_date"],
        )

        rows = await client.get_standings("PL")
        arsenal_row = next((r for r in rows if r.get("team_id") == ARSENAL_TEAM_ID), None)

        items = await fetch_all(FEEDS)
        articles = []
        seen_links: set[str] = set()
        for item in items:
            link = item.get("link")
            if not link or link in seen_links:
                continue
            full_text = f"{item.get('title', '')} {item.get('summary', '')}"
            if not (item["arsenal_only"] or matches_arsenal(full_text)):
                continue
            if is_women_content(full_text) or is_mocking_content(full_text):
                continue
            published = item.get("published_dt")
            if published is None or published < cutoff:
                continue
            seen_links.add(link)
            articles.append({"title": item.get("title", ""), "source": item.get("source", "")})

        log.info("Weekly: %d match(es), %d article(s)", len(recent_matches), len(articles))

        recap_text = await make_weekly_recap(llm, recent_matches, articles, arsenal_row)

        now = datetime.now(timezone.utc)
        week_str = f"{(now - LOOKBACK).strftime('%d/%m')}–{now.strftime('%d/%m/%Y')}"
        await fanout.send(formatting.format_weekly_recap(recap_text, week_str))
        log.info("Weekly recap sent")

    finally:
        await client.close()
        await llm.close()
        await fanout.close()


if __name__ == "__main__":
    asyncio.run(main())
