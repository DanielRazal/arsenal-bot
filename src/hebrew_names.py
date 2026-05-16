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
