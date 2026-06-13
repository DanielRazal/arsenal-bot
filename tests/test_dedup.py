from src.sources.dedup import find_similar, is_similar


def test_similar_english_same_story():
    assert is_similar(
        "Arsenal sign new midfielder from Barcelona",
        "Arsenal complete signing of new midfielder from Barcelona",
    )


def test_not_similar_english_different_story():
    assert not is_similar(
        "Arsenal sign new midfielder from Barcelona",
        "Arsenal complete defender deal with Real Madrid",
    )


def test_similar_hebrew_same_story():
    # Hebrew tokenizes now (Unicode block added to the regex).
    assert is_similar(
        "ארסנל חתמה על שחקן חדש מברצלונה",
        "דיווח: ארסנל מחתימה שחקן חדש מברצלונה",
    )


def test_not_similar_hebrew_different_story():
    assert not is_similar(
        "ארסנל ניצחה את צ'לסי בליגה",
        "ארסנל הפסידה לליברפול בגביע",
    )


def test_find_similar_returns_match():
    recent = ["Arsenal complete signing of new midfielder from Barcelona"]
    assert find_similar("Arsenal sign new midfielder from Barcelona", recent) == recent[0]
    assert find_similar("Totally unrelated tennis headline today", recent) is None
