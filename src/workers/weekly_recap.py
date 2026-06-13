"""Weekly Arsenal recap — scheduled worker version.

Ported from scripts/run_weekly_once.py (GitHub Actions, every Friday) so it runs
inside the always-on process. Fires Friday 19:00 Israel time and posts an
AI-written recap of the week's match(es), standings, and news.
"""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import formatting
from ..config import ARSENAL_TEAM_ID, TIMEZONE
from ..llm.client import LLMClient
from ..llm.weekly_recap import make_weekly_recap
from ..notifiers.fanout import Fanout
from ..sources.feeds import FEEDS, is_mocking_content, is_women_content, matches_arsenal
from ..sources.football_data import FootballDataClient
from ..sources.rss import fetch_all

log = logging.getLogger(__name__)

LOOKBACK = timedelta(days=7)


def _parse_iso(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


async def _run_weekly(client: FootballDataClient, llm: LLMClient, fanout: Fanout) -> None:
    cutoff = datetime.now(timezone.utc) - LOOKBACK

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

    log.info("weekly_recap: %d match(es), %d article(s)", len(recent_matches), len(articles))

    recap_text = await make_weekly_recap(llm, recent_matches, articles, arsenal_row)

    now = datetime.now(timezone.utc)
    week_str = f"{(now - LOOKBACK).strftime('%d/%m')}–{now.strftime('%d/%m/%Y')}"
    await fanout.send(formatting.format_weekly_recap(recap_text, week_str))
    log.info("weekly_recap sent")


def schedule(
    scheduler: AsyncIOScheduler,
    client: FootballDataClient,
    llm: LLMClient,
    fanout: Fanout,
) -> None:
    # Friday 19:00 Israel time (the old workflow's 16:00 UTC).
    trigger = CronTrigger(day_of_week="fri", hour=19, minute=0, timezone=TIMEZONE)
    scheduler.add_job(
        _run_weekly,
        trigger=trigger,
        args=[client, llm, fanout],
        id="weekly_recap",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    log.info("weekly_recap scheduled Friday 19:00 (%s)", TIMEZONE)
