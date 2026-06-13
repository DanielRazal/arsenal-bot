from src.sources.feeds import (
    is_clickbait,
    is_mocking_content,
    is_women_content,
    matches_arsenal,
)


def test_matches_arsenal_english():
    assert matches_arsenal("Arsenal sign a new player")
    assert matches_arsenal("Arteta praises Saka")


def test_matches_arsenal_hebrew():
    assert matches_arsenal("ארסנל ניצחה 2-0")
    assert matches_arsenal("התותחנים בדרך לאליפות")


def test_matches_arsenal_negative():
    assert not matches_arsenal("Chelsea beat Tottenham in the derby")
    assert not matches_arsenal("")


def test_is_clickbait():
    assert is_clickbait("Could Arsenal sign this striker?")
    assert is_clickbait("Report: Arsenal linked with a move")
    assert not is_clickbait("Arsenal sign striker officially")


def test_is_women_content():
    assert is_women_content("Arsenal Women beat Chelsea in the WSL")
    assert is_women_content("Beth Mead scores winner")
    assert not is_women_content("Arsenal beat Chelsea 2-0")


def test_is_mocking_content():
    assert is_mocking_content("Rivals troll Arsenal after defeat")
    assert is_mocking_content("[meme] funny moment")
    assert not is_mocking_content("Arsenal win at the Emirates")
