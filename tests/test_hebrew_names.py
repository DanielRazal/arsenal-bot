from src.hebrew_names import hebrewize, hebrewize_competition, hebrewize_team


def test_hebrewize_player():
    assert "סאקה" in hebrewize("Saka scored a great goal")
    assert "ארטטה" in hebrewize("Arteta said")


def test_hebrewize_team_full_name():
    assert hebrewize_team("Arsenal FC") == "ארסנל"
    assert hebrewize_team("Liverpool FC") == "ליברפול"
    assert hebrewize_team("Tottenham Hotspur FC") == "טוטנהאם"


def test_hebrewize_team_short_name():
    assert hebrewize_team("Man City") == "מנצ'סטר סיטי"
    assert hebrewize_team("Spurs") == "טוטנהאם"


def test_hebrewize_team_european():
    assert hebrewize_team("Real Madrid CF") == "ריאל מדריד"
    assert hebrewize_team("FC Barcelona") == "ברצלונה"


def test_hebrewize_team_unknown_falls_back():
    assert hebrewize_team("Some Random United") == "Some Random United"
    assert hebrewize_team("") == ""


def test_hebrewize_competition():
    assert hebrewize_competition("Premier League") == "פרמייר ליג"
    assert hebrewize_competition("UEFA Champions League") == "ליגת האלופות"
    assert hebrewize_competition("Unknown Cup") == "Unknown Cup"
