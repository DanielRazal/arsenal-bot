"""Player and manager name translations EN→HE for natural-sounding Hebrew output.

Used to localize names inside live alerts (goals, red cards) and to give the
LLM Hebrew names directly so its summaries don't transliterate awkwardly.

Coverage: Arsenal men's first-team squad as of 2025-26, plus the manager.
Keep keys lowercased for matching. Order keys longest-first when there's
overlap (e.g., 'declan rice' before 'rice') so we replace the most specific
match.
"""

# Lowercase EN → HE. Pairs are tried in order; longest first to avoid
# partial collisions (e.g. "ben white" before "white").
PLAYER_NAMES_EN_HE: list[tuple[str, str]] = [
    # Manager
    ("mikel arteta", "מיקל ארטטה"),
    ("arteta", "ארטטה"),

    # Goalkeepers
    ("david raya", "דייוויד ראיה"),
    ("raya", "ראיה"),
    ("karl hein", "קארל היין"),
    ("hein", "היין"),

    # Defenders — full names first
    ("william saliba", "ויליאם סאליבה"),
    ("saliba", "סאליבה"),
    ("gabriel magalhães", "גבריאל מגליאש"),
    ("gabriel magalhaes", "גבריאל מגליאש"),
    ("ben white", "בן וייט"),
    ("benjamin white", "בן וייט"),
    ("riccardo calafiori", "ריקרדו קלאפיורי"),
    ("calafiori", "קלאפיורי"),
    ("jurriën timber", "יוריאן טימבר"),
    ("jurrien timber", "יוריאן טימבר"),
    ("timber", "טימבר"),
    ("oleksandr zinchenko", "אולכסנדר זינצ'נקו"),
    ("zinchenko", "זינצ'נקו"),
    ("takehiro tomiyasu", "טקהירו טומיאסו"),
    ("tomiyasu", "טומיאסו"),
    ("piero hincapié", "פיירו הינקאפיה"),
    ("piero hincapie", "פיירו הינקאפיה"),
    ("hincapié", "הינקאפיה"),
    ("hincapie", "הינקאפיה"),
    ("cristhian mosquera", "כריסטיאן מוסקרה"),
    ("mosquera", "מוסקרה"),

    # Midfielders
    ("declan rice", "דקלן רייס"),
    ("rice", "רייס"),
    ("martin ødegaard", "מרטין אדגארד"),
    ("martin odegaard", "מרטין אדגארד"),
    ("ødegaard", "אדגארד"),
    ("odegaard", "אדגארד"),
    ("thomas partey", "תומאס פארטיי"),
    ("partey", "פארטיי"),
    ("mikel merino", "מיקל מרינו"),
    ("merino", "מרינו"),
    ("jorginho", "ג'ורג'יניו"),
    ("fabio vieira", "פאביו וייירה"),
    ("fábio vieira", "פאביו וייירה"),
    ("vieira", "וייירה"),
    ("ethan nwaneri", "איתן נואנרי"),
    ("nwaneri", "נואנרי"),
    ("myles lewis-skelly", "מיילס לואיס-סקלי"),
    ("lewis-skelly", "לואיס-סקלי"),
    ("martín zubimendi", "מרטין זובימנדי"),
    ("martin zubimendi", "מרטין זובימנדי"),
    ("zubimendi", "זובימנדי"),

    # Forwards
    ("bukayo saka", "בוקאיו סאקה"),
    ("saka", "סאקה"),
    ("gabriel martinelli", "גבריאל מרטינלי"),
    ("martinelli", "מרטינלי"),
    ("kai havertz", "קאי הברץ"),
    ("havertz", "הברץ"),
    ("gabriel jesus", "גבריאל ז'סוס"),
    ("leandro trossard", "לאנדרו טרוסארד"),
    ("trossard", "טרוסארד"),
    ("eddie nketiah", "אדי נקטיה"),
    ("nketiah", "נקטיה"),
    ("raheem sterling", "ראהים סטרלינג"),
    ("sterling", "סטרלינג"),
    ("viktor gyökeres", "ויקטור גיוקרש"),
    ("viktor gyokeres", "ויקטור גיוקרש"),
    ("gyökeres", "גיוקרש"),
    ("gyokeres", "גיוקרש"),
    ("noni madueke", "נוני מדואקה"),
    ("madueke", "מדואקה"),
    ("eberechi eze", "אברצ'י איזה"),
    ("eze", "איזה"),

    # Standalone "gabriel" goes last so the more-specific forms above win
    ("gabriel", "גבריאל"),
]


def hebrewize(text: str) -> str:
    """Replace player/manager names in text with Hebrew. Case-insensitive match."""
    if not text:
        return text
    result = text
    for en, he in PLAYER_NAMES_EN_HE:
        # Case-insensitive substring replace, preserving Hebrew output.
        idx = 0
        lowered = result.lower()
        while True:
            pos = lowered.find(en, idx)
            if pos == -1:
                break
            result = result[:pos] + he + result[pos + len(en):]
            lowered = result.lower()
            idx = pos + len(he)
    return result


# --- Team & competition name localization ---------------------------------
# football-data returns full names in matches ("Arsenal FC") and shortNames in
# standings ("Arsenal", "Man City"). We normalize by dropping club-type tokens
# and punctuation, then look up. Unknown teams fall back to the original
# (English) — the opponent long tail can't all be covered.
import re as _re
import unicodedata as _ud

_CLUB_TOKENS = {"fc", "afc", "cf", "sc", "ac", "as", "ssc", "ud", "cd", "club", "clube", "cp", "de"}
_TEAM_TOKEN_RE = _re.compile(r"[a-z']+")


def _strip_accents(s: str) -> str:
    return "".join(c for c in _ud.normalize("NFKD", s) if not _ud.combining(c))


def _norm_team(name: str) -> str:
    # Strip diacritics ("Atlético" -> "atletico") then drop club-type tokens, so
    # both full match names and shortNames map to the same key.
    s = _strip_accents(name.lower())
    toks = [t for t in _TEAM_TOKEN_RE.findall(s) if t not in _CLUB_TOKENS]
    return " ".join(toks)


# Keys are normalized (lowercase, club tokens dropped). Multiple aliases per
# club cover both the full match name and the standings shortName.
TEAMS_EN_HE: dict[str, str] = {
    # Premier League
    "arsenal": "ארסנל",
    "aston villa": "אסטון וילה",
    "bournemouth": "בורנמות'",
    "brentford": "ברנטפורד",
    "brighton hove albion": "ברייטון", "brighton hove": "ברייטון", "brighton": "ברייטון",
    "burnley": "ברנלי",
    "chelsea": "צ'לסי",
    "crystal palace": "קריסטל פאלאס",
    "everton": "אוורטון",
    "fulham": "פולהאם",
    "ipswich town": "איפסוויץ'", "ipswich": "איפסוויץ'",
    "leeds united": "לידס", "leeds": "לידס",
    "leicester city": "לסטר", "leicester": "לסטר",
    "liverpool": "ליברפול",
    "manchester city": "מנצ'סטר סיטי", "man city": "מנצ'סטר סיטי",
    "manchester united": "מנצ'סטר יונייטד", "man united": "מנצ'סטר יונייטד",
    "newcastle united": "ניוקאסל", "newcastle": "ניוקאסל",
    "nottingham forest": "נוטינגהאם פורסט", "nott'm forest": "נוטינגהאם פורסט", "nottingham": "נוטינגהאם פורסט",
    "southampton": "סאות'המפטון",
    "sunderland": "סנדרלנד",
    "tottenham hotspur": "טוטנהאם", "tottenham": "טוטנהאם", "spurs": "טוטנהאם",
    "west ham united": "וסטהאם", "west ham": "וסטהאם",
    "wolverhampton wanderers": "וולבס", "wolverhampton": "וולבס", "wolves": "וולבס",
    # Frequent European opponents
    "real madrid": "ריאל מדריד",
    "barcelona": "ברצלונה",
    "atletico madrid": "אתלטיקו מדריד", "atlético de madrid": "אתלטיקו מדריד", "atletico de madrid": "אתלטיקו מדריד",
    "bayern münchen": "באיירן מינכן", "bayern munchen": "באיירן מינכן", "bayern munich": "באיירן מינכן",
    "borussia dortmund": "דורטמונד", "dortmund": "דורטמונד",
    "paris saint germain": "פ.ס.ז'", "psg": "פ.ס.ז'",
    "internazionale milano": "אינטר", "inter": "אינטר",
    "milan": "מילאן",
    "juventus": "יובנטוס",
    "napoli": "נאפולי",
    "porto": "פורטו",
    "benfica": "בנפיקה",
    "ajax": "אייאקס",
    "bayer leverkusen": "באייר לברקוזן", "leverkusen": "לברקוזן",
    "sporting portugal": "ספורטינג ליסבון", "sporting": "ספורטינג ליסבון",
}

COMPETITIONS_EN_HE: dict[str, str] = {
    "premier league": "פרמייר ליג",
    "uefa champions league": "ליגת האלופות",
    "uefa europa league": "ליגה האירופית",
    "uefa europa conference league": "ליגת הקונפרנס",
    "uefa conference league": "ליגת הקונפרנס",
    "fa cup": "גביע ה-FA",
    "efl cup": "גביע הליגה",
    "football league cup": "גביע הליגה",
    "carabao cup": "גביע הליגה",
    "fa community shield": "מגן הקומיוניטי",
    "community shield": "מגן הקומיוניטי",
    "fifa club world cup": "גביע העולם למועדונים",
    "club friendlies": "משחקי ידידות",
}


def hebrewize_team(name: str) -> str:
    """Localize a club name to Hebrew; unknown clubs return unchanged."""
    if not name:
        return name
    return TEAMS_EN_HE.get(_norm_team(name), name)


def hebrewize_competition(name: str) -> str:
    """Localize a competition name to Hebrew; unknown ones return unchanged."""
    if not name:
        return name
    return COMPETITIONS_EN_HE.get(name.strip().lower(), name)
