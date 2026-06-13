"""Cross-source story deduplication.

When BBC, Guardian and Arseblog all publish "Saka signs new contract"
within a few minutes of each other, we want to push only one alert.

Approach: normalize each title (strip punctuation, lowercase, drop short
and stopword tokens) and compute Jaccard similarity on the remaining
content words. Above SIMILARITY_THRESHOLD they're considered the same story.
"""
from __future__ import annotations

import re

SIMILARITY_THRESHOLD = 0.5
MIN_SHARED_TOKENS = 3

# Words that don't carry story-identity meaning. Kept minimal — only obvious
# noise. Real content words (player surnames, verbs like "signs", "extends")
# stay in to drive overlap.
STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to", "for",
        "with", "by", "as", "is", "are", "was", "were", "be", "been", "being",
        "from", "into", "after", "before", "over", "under", "this", "that",
        "these", "those", "it", "its", "his", "her", "their", "our", "we",
        "you", "your", "my", "mine", "yours",
        # Common sports/news connectors that appear in nearly every title
        "vs", "v", "report", "news", "preview", "match", "matchday",
        # Hebrew connectors / news-noise that carry no story identity
        "דיווח", "חדשות", "עדכון", "כתבה", "היום", "אתמול", "אחרי",
        "לפני", "הבוקר", "הערב", "אמש", "וידאו", "תיעוד", "צפו", "האם",
        "מול", "נגד", "עוד", "כבר", "הוא", "היא", "הם", "גם",
    }
)

# Include the Hebrew block (U+0590–U+05FF) so Hebrew titles tokenize too —
# without this, Hebrew headlines produced empty token sets and cross-source
# dedup never fired for Hebrew articles.
_WORD_RE = re.compile(r"[A-Za-z0-9֐-׿']+")


def _tokens(title: str) -> set[str]:
    if not title:
        return set()
    out = set()
    for raw in _WORD_RE.findall(title.lower()):
        if len(raw) < 3:
            continue
        if raw in STOPWORDS:
            continue
        out.add(raw)
    return out


def is_similar(title_a: str, title_b: str, *, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    """True if the two titles look like the same story.

    Uses Jaccard similarity on filtered word tokens, plus a minimum
    shared-token floor so very short titles ('Arsenal beat X' vs 'Arsenal
    beat Y') don't get falsely merged.
    """
    a, b = _tokens(title_a), _tokens(title_b)
    if len(a) < 3 or len(b) < 3:
        return False
    shared = len(a & b)
    if shared < MIN_SHARED_TOKENS:
        return False
    union = len(a | b)
    if union == 0:
        return False
    return (shared / union) >= threshold


def find_similar(title: str, candidates: list[str], *, threshold: float = SIMILARITY_THRESHOLD) -> str | None:
    """Return the first candidate that looks like the same story, or None."""
    for c in candidates:
        if is_similar(title, c, threshold=threshold):
            return c
    return None
