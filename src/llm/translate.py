"""Translate English news headlines to Hebrew for the news feed.

Israeli media barely covers Arsenal, so the bot also pulls Arsenal-dedicated
English feeds (BBC, Guardian, Arseblog) and runs their headlines through the
LLM here, so the user still reads everything in Hebrew. Translation failures
fall back to the original text — a missed translation must never drop an alert.
"""
import logging

from ..hebrew_names import hebrewize
from .client import LLMClient

log = logging.getLogger(__name__)

_SYSTEM = (
    "You translate football news headlines for an Arsenal FC fan channel from "
    "English to Hebrew. Return ONE natural, concise Hebrew headline — keep it "
    "punchy, no quotes, no preamble, no explanation, Hebrew only. Keep proper "
    "nouns (player/club names) accurate."
)


async def translate_title(llm: LLMClient, title: str) -> str:
    """English headline -> Hebrew. Returns the original on any failure."""
    if not title or not title.strip():
        return title
    try:
        out = await llm.complete(_SYSTEM, title, max_tokens=120)
    except Exception:
        log.exception("Headline translation failed; using original")
        return title
    out = (out or "").strip().strip('"').strip("'").strip()
    if not out:
        return title
    # Normalize known Arsenal player/manager names if the model left any in English.
    return hebrewize(out)
