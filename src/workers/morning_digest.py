import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import db
from ..config import MORNING_DIGEST_HOUR, TIMEZONE
from ..llm.article_digest import make_digest
from ..llm.client import LLMClient

log = logging.getLogger(__name__)


async def _run_digest(llm: LLMClient, on_digest) -> None:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    articles = db.get_articles_for_digest(since)
    log.info("morning_digest: %d articles to summarize", len(articles))
    if not articles:
        await on_digest("_אין כתבות חדשות מאז אתמול._", 0)
        return
    digest_text = await make_digest(llm, articles)
    await on_digest(digest_text, len(articles))
    db.mark_articles_in_digest([a["link"] for a in articles])


def schedule(scheduler: AsyncIOScheduler, llm: LLMClient, on_digest) -> None:
    trigger = CronTrigger(hour=MORNING_DIGEST_HOUR, minute=0, timezone=TIMEZONE)
    scheduler.add_job(
        _run_digest,
        trigger=trigger,
        args=[llm, on_digest],
        id="morning_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    log.info("morning_digest scheduled daily at %02d:00 %s", MORNING_DIGEST_HOUR, TIMEZONE)
