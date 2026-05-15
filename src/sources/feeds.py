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
