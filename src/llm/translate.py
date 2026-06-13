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


_TRANSLIT_SYSTEM = (
    "Transliterate each footballer name from English to Hebrew (phonetic "
    "spelling, as Israeli sports media would write it). Return the SAME numbered "
    "list — each line '<number>. <Hebrew name>', same order, Hebrew only, no "
    "English, no extra text."
)

_NUM_LINE = __import__("re").compile(r"^\s*(\d+)[.)]\s*(.+?)\s*$")


async def transliterate_names(llm: LLMClient, names: list[str]) -> dict[str, str]:
    """Map English footballer names -> Hebrew via one LLM call (by list index,
    so it's robust to the model not echoing the English). Returns {} on failure
    (callers keep the original English)."""
    if not names:
        return {}
    listing = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(names))
    try:
        out = await llm.complete(_TRANSLIT_SYSTEM, listing, max_tokens=900)
    except Exception:
        log.exception("Squad name transliteration failed; keeping originals")
        return {}
    mapping: dict[str, str] = {}
    for line in (out or "").splitlines():
        m = _NUM_LINE.match(line)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(names):
            mapping[names[idx]] = m.group(2)
    return mapping
