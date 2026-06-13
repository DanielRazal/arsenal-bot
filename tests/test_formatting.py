from src import formatting as F

MATCH = {
    "utc_date": "2026-08-15T16:30:00Z",
    "competition": "Premier League",
    "home_team": "Arsenal FC",
    "away_team": "Liverpool FC",
    "home_team_id": 57,
    "away_team_id": 64,
    "score_home": 1,
    "score_away": 1,
}


def test_goal_localizes_team_and_competition():
    out = F.format_goal({"match": MATCH, "minute": 23, "scorer": "Bukayo Saka", "team": "Arsenal FC", "is_arsenal": True})
    assert "ארסנל" in out
    assert "ליברפול" in out
    assert "בוקאיו סאקה" in out  # player hebrewized
    assert "Arsenal" not in out  # no leftover English club name


def test_prematch_hebrew():
    out = F.format_prematch(MATCH)
    assert "פרמייר ליג" in out
    assert "Premier League" not in out
    assert "נגד" in out


def test_standings_localized():
    rows = [
        {"position": 1, "team_name": "Man City", "team_id": 65, "points": 9, "goal_difference": 6, "played": 3},
        {"position": 2, "team_name": "Arsenal", "team_id": 57, "points": 7, "goal_difference": 4, "played": 3},
    ]
    out = F.format_standings(rows)
    assert "פרמייר ליג" in out
    assert "מנצ'סטר סיטי" in out
    assert "נק'" in out
    assert "pts" not in out


def test_news_item_format():
    out = F.format_news_item({"title": "כותרת", "source": "Ynet", "link": "https://x.co"})
    assert "כותרת" in out and "Ynet" in out
