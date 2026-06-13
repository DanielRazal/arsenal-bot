# Mostly Hebrew/Israeli sources (English sources removed by request), plus one
# English exception: Fabrizio Romano's column for transfers. All are broad
# feeds filtered to Arsenal by keyword anywhere in the article (title or body).
# Cross-source duplicates are handled by dedup.py (Hebrew-aware).
# NOTE: this is news only. Live match alerts (goals, scores, pre-match,
# half-time, post-match summary) come from the football-data API and are
# unaffected by this list.
FEEDS = [
    {"source": "Ynet ספורט", "url": "https://www.ynet.co.il/Integration/StoryRss3.xml", "arsenal_only": False},
    {"source": "Walla כדורגל עולמי", "url": "https://rss.walla.co.il/feed/316", "arsenal_only": False},
    {"source": "Maariv ספורט", "url": "https://www.maariv.co.il/Rss/RssFeedsSport", "arsenal_only": False},
    # English exception: Fabrizio Romano transfer column (via CaughtOffside,
    # which aggregates/cites his reports — closest RSS-able proxy; his X/IG/
    # TikTok have no usable feed). title_match_only keeps only items with
    # "Arsenal" in the headline — "Arsenal transfers only", no passing mentions.
    {"source": "פבריציו רומאנו", "url": "https://caughtoffside.com/tag/fabrizio-romano/feed/", "arsenal_only": False, "title_match_only": True},
]

ARSENAL_KEYWORDS = [
    "arsenal", "gunners", "arteta", "saka", "ødegaard", "odegaard",
    "rice", "saliba", "gabriel", "havertz", "martinelli", "white",
    "raya", "trossard", "jesus", "zinchenko", "tomiyasu", "emirates",
    "ארסנל", "התותחנים", "ארטטה", "סאקה", "אדגארד",
]


def matches_arsenal(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(kw in lowered for kw in ARSENAL_KEYWORDS)


CLICKBAIT_PREFIXES = (
    "could ", "might ", "reportedly ", "rumour ", "rumor ",
    "report:", "report -", "exclusive:", "exclusive -",
    "would ", "may ", "set to ", "tipped to ", "linked with ",
    "in line for ", "considering ", "interested in ",
)

CLICKBAIT_PHRASES = (
    " could join ", " could leave ", " could sign ",
    " linked with a move ", " set for shock ",
    " transfer rumour ", " transfer rumor ",
)


def is_clickbait(title: str) -> bool:
    """Speculative transfer-rumor titles — keep in DB for digest, skip push."""
    if not title:
        return False
    lowered = title.lower().lstrip()
    if any(lowered.startswith(prefix) for prefix in CLICKBAIT_PREFIXES):
        return True
    if any(phrase in lowered for phrase in CLICKBAIT_PHRASES):
        return True
    return False


WOMEN_KEYWORDS = (
    "arsenal women", "arsenal ladies", "awfc",
    " wsl ", " wsl:", " uwcl ",
    "women's super league", "women's champions league",
    "barclays women",
    # Known Arsenal Women players (lowercased, full names only to avoid
    # false positives with men's team players)
    "beth mead", "vivianne miedema", "alessia russo",
    "caitlin foord", "steph catley", "frida maanum",
    "manuela zinsberger", "leah williamson", "katie mccabe",
    "lia walti", "lia wälti", "stina blackstenius",
    "lotte wubben-moy", "rosa kafaji", "michelle agyemang",
    "victoria pelova", "kim little", "renee slegers",
)


def is_women_content(text: str) -> bool:
    """True if the text is about Arsenal Women's team."""
    if not text:
        return False
    lowered = f" {text.lower()} "  # pad so word-boundary patterns match
    return any(kw in lowered for kw in WOMEN_KEYWORDS)


CONFIRMED_TRANSFER_KEYWORDS = (
    " signs ", " signed ", " joins ", " joined ",
    " completes ", " completed ", "done deal", "official:",
    " confirmed", " announces ", " unveiled ",
)

INJURY_KEYWORDS = (
    " injured", " injury", " ruled out", " out for ",
    " sidelined", " fracture", " ligament", " hamstring",
    " muscle injury", " scan result", " surgery",
    " פציעה", " נפצע", " ייעדר",
)


def is_confirmed_transfer(text: str) -> bool:
    if not text:
        return False
    lowered = f" {text.lower()} "
    return any(kw in lowered for kw in CONFIRMED_TRANSFER_KEYWORDS)


def is_injury_news(text: str) -> bool:
    if not text:
        return False
    lowered = f" {text.lower()} "
    return any(kw in lowered for kw in INJURY_KEYWORDS)


MOCKING_PATTERNS = (
    # Direct mockery / banter
    "spursy",
    "bottlejob", "bottle job",
    "arsenal trolled", "trolling arsenal", "trolled arsenal",
    "arsenal mocked", "mocking arsenal", "mocked arsenal",
    "arsenal laughing stock", "arsenal laughing-stock", "laughingstock",
    "fans mock arsenal", "rivals mock arsenal",
    "rivals troll arsenal", "twitter mocks arsenal", "twitter trolls arsenal",
    "rinsed arsenal", "roasted arsenal",
    # Meme / shitpost markers
    "shitpost", "shit post", "shitposting",
    "[meme]", "[memes]", "[shitpost]", "[banter]",
    " banter ",
)


def is_mocking_content(text: str) -> bool:
    """True if the text is mocking/joking about Arsenal in a hostile way."""
    if not text:
        return False
    lowered = f" {text.lower()} "  # pad so word-boundary patterns match
    return any(pattern in lowered for pattern in MOCKING_PATTERNS)
