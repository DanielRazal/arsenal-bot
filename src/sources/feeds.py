FEEDS = [
    {"source": "Arseblog", "url": "https://arseblog.com/feed/", "arsenal_only": True},
    {"source": "Reddit r/Gunners", "url": "https://www.reddit.com/r/Gunners/.rss", "arsenal_only": True},
    {"source": "Sky Sports — Premier League", "url": "https://www.skysports.com/rss/12040", "arsenal_only": False},
    {"source": "BBC Sport — Arsenal", "url": "https://feeds.bbci.co.uk/sport/football/teams/arsenal/rss.xml", "arsenal_only": True},
    {"source": "The Guardian — Arsenal", "url": "https://www.theguardian.com/football/arsenal/rss", "arsenal_only": True},
]

ARSENAL_KEYWORDS = [
    "arsenal", "gunners", "arteta", "saka", "ødegaard", "odegaard",
    "rice", "saliba", "gabriel", "havertz", "martinelli", "white",
    "raya", "trossard", "jesus", "zinchenko", "tomiyasu", "emirates",
    "ארסנל", "ארטטה", "סאקה", "אדגארד",
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
