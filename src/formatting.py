from datetime import datetime
from zoneinfo import ZoneInfo

from .config import ARSENAL_TEAM_ID, TIMEZONE


def _local_time(utc_iso: str) -> str:
    dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(TIMEZONE)).strftime("%H:%M %d/%m")


def format_prematch(match: dict) -> str:
    kickoff = _local_time(match["utc_date"])
    competition = match.get("competition") or "משחק"
    home = match["home_team"]
    away = match["away_team"]
    return (
        f"⚽ *משחק בעוד 30 דקות!*\n"
        f"🏆 {competition}\n"
        f"🆚 {home} vs {away}\n"
        f"🕒 {kickoff}\n"
        f"בוא נראה אותם 💪"
    )


def format_goal(event: dict) -> str:
    match = event["match"]
    minute = event.get("minute", "?")
    scorer = event.get("scorer", "Unknown")
    team = event.get("team", "")
    is_arsenal = event.get("is_arsenal", False)
    score = f"{match.get('score_home') or 0}–{match.get('score_away') or 0}"
    home = match["home_team"]
    away = match["away_team"]
    emoji = "🔴⚪ *גוווולllll!!!*" if is_arsenal else "😡 שער ליריבים"
    return (
        f"{emoji}\n"
        f"⏱ דקה {minute}' — {scorer} ({team})\n"
        f"📊 {home} {score} {away}"
    )


def format_red_card(event: dict) -> str:
    match = event["match"]
    minute = event.get("minute", "?")
    player = event.get("player", "Unknown")
    team = event.get("team", "")
    is_arsenal = event.get("is_arsenal", False)
    second_yellow = event.get("second_yellow", False)
    card_desc = "כרטיס צהוב שני" if second_yellow else "כרטיס אדום ישיר"
    if is_arsenal:
        verdict = f"🟥 *הורחק!* (לרעתנו)\n⏱ דקה {minute}' — {player}\n{card_desc} 😡"
    else:
        verdict = f"🟥 *הורחק יריב!* 🎉\n⏱ דקה {minute}' — {player} ({team})\n{card_desc} — עכשיו אנחנו ביתרון מספרי"
    score = f"{match.get('score_home') or 0}–{match.get('score_away') or 0}"
    home = match["home_team"]
    away = match["away_team"]
    return f"{verdict}\n📊 {home} {score} {away}"


def format_halftime(match: dict) -> str:
    home = match["home_team"]
    away = match["away_team"]
    score_home = match.get("score_home") or 0
    score_away = match.get("score_away") or 0
    arsenal_home = match.get("home_team_id") == ARSENAL_TEAM_ID
    arsenal_score = score_home if arsenal_home else score_away
    opp_score = score_away if arsenal_home else score_home
    if arsenal_score > opp_score:
        mood = "_מובילים, עוד 45 דקות להיאחז_ 💪"
    elif arsenal_score == opp_score:
        mood = "_עוד 45 דקות לשבור את התיקו_"
    else:
        mood = "_פיגור, צריך מהפך בחצי השני_ 😤"
    return (
        f"⏸ *חצי משחק*\n"
        f"📊 {home} {score_home}–{score_away} {away}\n"
        f"{mood}"
    )


def format_match_finished(match: dict, summary_text: str) -> str:
    home = match["home_team"]
    away = match["away_team"]
    score = f"{match.get('score_home') or 0}–{match.get('score_away') or 0}"
    arsenal_home = match.get("home_team_id") == ARSENAL_TEAM_ID
    arsenal_score = match.get("score_home") if arsenal_home else match.get("score_away")
    opp_score = match.get("score_away") if arsenal_home else match.get("score_home")
    if arsenal_score is None or opp_score is None:
        verdict = "📋 *סיכום המשחק*"
    elif arsenal_score > opp_score:
        verdict = "🎉 *ניצחון!*"
    elif arsenal_score == opp_score:
        verdict = "🤝 *תיקו*"
    else:
        verdict = "😔 *הפסד*"
    return (
        f"{verdict}\n"
        f"📊 {home} {score} {away}\n\n"
        f"{summary_text}"
    )


def format_news_item(article: dict) -> str:
    title = article.get("title", "")
    source = article.get("source", "")
    link = article.get("link", "")
    return f"📰 *{title}*\n🔗 [{source}]({link})"


def format_morning_digest(digest_text: str, article_count: int) -> str:
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d/%m/%Y")
    return (
        f"☀️ *סיכום בוקר — {today}*\n"
        f"_{article_count} כתבות מהיממה האחרונה_\n\n"
        f"{digest_text}"
    )
