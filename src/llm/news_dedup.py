"""LLM-based semantic duplicate detection for news headlines.

Token-overlap dedup (src/sources/dedup.py) is a cheap first pass, but it misses
paraphrased duplicates that share few words — e.g. "Arsenal linked with Greek
winger" vs "Arsenal consider move for Greek forward Tzolis" (same transfer
saga, different wording, possibly different languages). This second pass asks
the LLM whether a new headline is the same story as any recent one.

On any failure we return False (not a duplicate) — a flaky LLM must never
silently swallow real news.
"""
import logging

from .client import LLMClient

log = logging.getLogger(__name__)

# Cap how many recent headlines we compare against, to bound prompt size/cost.
_MAX_RECENT = 25

_SYSTEM = (
    "You detect duplicate football news. Two headlines are the SAME story if "
    "they cover the same specific event/transfer saga/match — even if worded "
    "differently or written in different languages (e.g. English vs Hebrew). "
    "Different events are NOT duplicates, even if they share a club or topic. "
    "Answer with a single word: YES or NO."
)


async def is_duplicate_story(llm: LLMClient, title: str, recent_titles: list[str]) -> bool:
    if not title or not recent_titles:
        return False
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(recent_titles[:_MAX_RECENT]))
    user = (
        f"NEW headline:\n{title}\n\n"
        f"RECENT headlines already sent:\n{numbered}\n\n"
        f"Is the NEW headline the same story as ANY recent one? Answer YES or NO."
    )
    try:
        out = await llm.complete(_SYSTEM, user, max_tokens=5)
    except Exception:
        log.exception("Semantic dedup check failed; treating as not-duplicate")
        return False
    return (out or "").strip().upper().startswith("Y")
