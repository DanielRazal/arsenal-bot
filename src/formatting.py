from datetime import datetime
from zoneinfo import ZoneInfo

from .config import ARSENAL_TEAM_ID, TIMEZONE
from .hebrew_names import hebrewize, hebrewize_team, hebrewize_competition


def _local_time(utc_iso: str) -> str:
    dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(TIMEZONE)).strftime("%H:%M %d/%m")


def format_prematch(match: dict) -> str:
    kickoff = _local_time(match["utc_date"])
    competition = hebrewize_competition(match.get("competition") or "משחק")
    home = hebrewize_team(match["home_team"])
    away = hebrewize_team(match["away_team"])
    return (
        f"⚽ *משחק בעוד 30 דקות!*\n"
        f"🏆 {competition}\n"
        f"🆚 {home} נגד {away}\n"
        f"🕒 {kickoff}\n"
        f"בוא נראה אותם 💪"
    )


def format_goal(event: dict) -> str:
    match = event["match"]
    minute = event.get("minute", "?")
    scorer = hebrewize(event.get("scorer", "Unknown"))
    team = hebrewize_team(event.get("team", ""))
    is_arsenal = event.get("is_arsenal", False)
    score = f"{match.get('score_home') or 0}–{match.get('score_away') or 0}"
    home = hebrewize_team(match["home_team"])
    away = hebrewize_team(match["away_team"])
    emoji = "🔴⚪ *גוווולllll!!!*" if is_arsenal else "😡 שער ליריבים"
    return (
        f"{emoji}\n"
        f"⏱ דקה {minute}' — {scorer} ({team})\n"
        f"📊 {home} {score} {away}"
    )


def format_red_card(event: dict) -> str:
    match = event["match"]
    minute = event.get("minute", "?")
    player = hebrewize(event.get("player", "Unknown"))
    team = hebrewize_team(event.get("team", ""))
    is_arsenal = event.get("is_arsenal", False)
    second_yellow = event.get("second_yellow", False)
    card_desc = "כרטיס צהוב שני" if second_yellow else "כרטיס אדום ישיר"
    if is_arsenal:
        verdict = f"🟥 *הורחק!* (לרעתנו)\n⏱ דקה {minute}' — {player}\n{card_desc} 😡"
    else:
        verdict = f"🟥 *הורחק יריב!* 🎉\n⏱ דקה {minute}' — {player} ({team})\n{card_desc} — עכשיו אנחנו ביתרון מספרי"
    score = f"{match.get('score_home') or 0}–{match.get('score_away') or 0}"
    home = hebrewize_team(match["home_team"])
    away = hebrewize_team(match["away_team"])
    return f"{verdict}\n📊 {home} {score} {away}"


def format_halftime(match: dict) -> str:
    home = hebrewize_team(match["home_team"])
    away = hebrewize_team(match["away_team"])
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
    home = hebrewize_team(match["home_team"])
    away = hebrewize_team(match["away_team"])
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


def format_next_matches(matches: list[dict]) -> str:
    if not matches:
        return "📅 *אין משחקים בלוח הזמנים הקרוב*\n_(או שה-API לא מחזיר נכון, נסה שוב מאוחר יותר)_"
    lines = ["📅 *המשחקים הבאים של ארסנל*", ""]
    for i, match in enumerate(matches, 1):
        kickoff = _local_time(match["utc_date"])
        competition = hebrewize_competition(match.get("competition") or "")
        home = hebrewize_team(match["home_team"])
        away = hebrewize_team(match["away_team"])
        venue_indicator = "🏠" if match.get("home_team_id") == ARSENAL_TEAM_ID else "✈️"
        lines.append(f"{i}. {venue_indicator} {home} נגד {away}")
        lines.append(f"   🕒 {kickoff} · 🏆 {competition}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_standings(rows: list[dict]) -> str:
    if not rows:
        return "📊 *לא הצלחתי לשלוף את טבלת הליגה כרגע*"
    arsenal_row = next((r for r in rows if r.get("team_id") == ARSENAL_TEAM_ID), None)
    played = rows[0].get("played", 0) if rows else 0

    # LRM keeps the signed goal-difference reading "+44" not "44+". Per-line
    # RTL alignment is applied centrally in the Telegram notifier.
    lrm = "\u200e"
    lines = [f"🏆 *פרמייר ליג · מחזור {played}*", ""]
    for row in rows:
        rank = row.get("position", 0)
        name = hebrewize_team(row.get("team_name", ""))
        points = row.get("points", 0)
        gd = row.get("goal_difference", 0)
        gd_str = f"+{gd}" if (gd or 0) > 0 else str(gd)
        gd_disp = f"({lrm}{gd_str}{lrm})"
        is_arsenal = row.get("team_id") == ARSENAL_TEAM_ID
        if is_arsenal:
            lines.append(f"{rank}. *{name} — {points} נק'* {gd_disp}")
        else:
            lines.append(f"{rank}. {name} — {points} נק' {gd_disp}")
        if rank == 4 or rank == 17:
            lines.append("━━━━━━━━━━━━━━━━━━")

    lines.append("")
    if arsenal_row is not None:
        if arsenal_row.get("position", 0) == 1:
            lines.append("🥇 _מובילים בליגה!_")
        else:
            leader = rows[0]
            gap = (leader.get("points") or 0) - (arsenal_row.get("points") or 0)
            leader_name = hebrewize_team(leader.get("team_name") or "")
            if gap == 0:
                lines.append(f"_שווים בנקודות עם {leader_name}_ 🤝")
            else:
                lines.append(f"_פער של {gap} נקודות מ-{leader_name}_")
    return "\n".join(lines)


def format_spurs_loss(match: dict) -> str:
    home = hebrewize_team(match["home_team"])
    away = hebrewize_team(match["away_team"])
    score = f"{match.get('score_home') or 0}–{match.get('score_away') or 0}"
    competition = hebrewize_competition(match.get("competition") or "משחק")
    return (
        f"🎉 *טוטנהאם הפסידו שוב!* 🍿\n"
        f"🏆 {competition}\n"
        f"📊 {home} {score} {away}\n"
        f"_עוד יום טוב להיות גאנר._"
    )


def format_help() -> str:
    return (
        "🔴⚪ *פקודות הבוט של ארסנל*\n\n"
        "/next — המשחקים הקרובים של ארסנל\n"
        "/fixtures — לוח המשחקים המלא\n"
        "/last — סיכום המשחק האחרון עם ניתוח AI\n"
        "/form — 5 התוצאות האחרונות\n"
        "/standings — טבלת הפרמיירליג\n"
        "/scorers — מובילי הבקיעים בליגה\n"
        "/squad — הרכב הקבוצה הנוכחי\n"
        "/stats — מבקיעי ארסנל בליגה\n"
        "/help — התפריט הזה\n\n"
        "_התראות אוטומטיות: גולים, כרטיסים אדומים, חצי גמר, סיכום משחק, חדשות, העברות, פציעות, Spurs שהפסידו ועוד._"
    )


def format_transfer_alert(article: dict) -> str:
    title = article.get("title", "")
    source = article.get("source", "")
    link = article.get("link", "")
    return f"🚨 *העברה רשמית!*\n{title}\n🔗 [{source}]({link})"


def format_injury_alert(article: dict) -> str:
    title = article.get("title", "")
    source = article.get("source", "")
    link = article.get("link", "")
    return f"🏥 *עדכון פציעה*\n{title}\n🔗 [{source}]({link})"


_POSITION_EMOJI = {
    "Goalkeeper": "🧤",
    "Defender": "🛡️",
    "Midfielder": "⚙️",
    "Attacker": "⚡",
}

_POSITION_LABEL = {
    "Goalkeeper": "שוערים",
    "Defender": "מגנים",
    "Midfielder": "קשרים",
    "Attacker": "חלוצים",
}

_POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Attacker"]


def format_squad(players: list[dict]) -> str:
    if not players:
        return "לא הצלחתי לשלוף את ההרכב כרגע."
    grouped: dict[str, list[dict]] = {p: [] for p in _POSITION_ORDER}
    for player in players:
        pos = player.get("position", "")
        if pos in grouped:
            grouped[pos].append(player)
    total = sum(len(v) for v in grouped.values())
    lines = [f"👥 *הרכב ארסנל* ({total} שחקנים)"]
    for pos in _POSITION_ORDER:
        group = grouped[pos]
        if not group:
            continue
        emoji = _POSITION_EMOJI[pos]
        label = _POSITION_LABEL[pos]
        lines.append(f"\n{emoji} *{label}*")
        for p in sorted(group, key=lambda x: x.get("name", "")):
            name = hebrewize(p["name"])
            age = f" · {p['age']}" if p.get("age") else ""
            lines.append(f"• {name}{age}")
    lines.append(f"\n_{total} שחקנים · נתונים מ-ESPN_")
    return "\n".join(lines)


def format_stats(scorers: list[dict]) -> str:
    if not scorers:
        return "אין שחקני ארסנל ברשימת המבקיעים הבולטים כרגע."
    lines = ["📊 *מבקיעי ארסנל בליגה — עונה נוכחית*", ""]
    for i, s in enumerate(scorers, 1):
        name = hebrewize(s["player_name"])
        goals = s["goals"]
        penalties = s.get("penalties", 0)
        pen_str = f" _(כולל {penalties} פנדל)_" if penalties else ""
        lines.append(f"{i}. {name} — {goals} ⚽{pen_str}")
    return "\n".join(lines)


def format_scorers(scorers: list[dict]) -> str:
    if not scorers:
        return "לא הצלחתי לשלוף את מובילי הבקיעים כרגע."
    lines = ["⚽ *מובילי הבקיעים בפרמייר ליג*", ""]
    for i, s in enumerate(scorers[:10], 1):
        name = hebrewize(s.get("player_name", ""))
        team = hebrewize_team(s.get("team_name", ""))
        goals = s.get("goals", 0) or 0
        lines.append(f"{i}. {name} ({team}) — {goals} ⚽")
    return "\n".join(lines)


def format_form(matches: list[dict]) -> str:
    if not matches:
        return "לא מצאתי משחקים אחרונים."
    lines = ["📋 *5 המשחקים האחרונים של ארסנל*", ""]
    for m in matches[:5]:
        arsenal_home = m.get("home_team_id") == ARSENAL_TEAM_ID
        ars = (m.get("score_home") if arsenal_home else m.get("score_away")) or 0
        opp = (m.get("score_away") if arsenal_home else m.get("score_home")) or 0
        opp_name = hebrewize_team(m.get("away_team") if arsenal_home else m.get("home_team"))
        if ars > opp:
            res = "✅ ניצחון"
        elif ars == opp:
            res = "🤝 תיקו"
        else:
            res = "❌ הפסד"
        venue = "🏠" if arsenal_home else "✈️"
        lines.append(f"{res} {ars}-{opp} {venue} נגד {opp_name}")
    return "\n".join(lines)


def format_standings_alert(event: str, arsenal_row: dict, prev_position: int | None) -> str:
    pos = arsenal_row.get("position", "?")
    pts = arsenal_row.get("points", "?")
    gd = arsenal_row.get("goal_difference", 0) or 0
    gd_str = f"+{gd}" if gd > 0 else str(gd)

    if event == "first":
        headline = "🥇 *ארסנל עולים למקום ראשון!*"
    elif event == "dropped_first":
        headline = f"📉 *ארסנל ירדו ממקום ראשון — עכשיו במקום {pos}*"
    elif event == "top4_in":
        headline = f"📈 *ארסנל חזרו לטופ 4! מקום {pos}*"
    else:
        headline = f"⚠️ *ארסנל יצאו מהטופ 4 — עכשיו במקום {pos}*"

    return (
        f"{headline}\n"
        f"🏆 פרמייר ליג\n"
        f"📊 {pts} נקודות | הפרש שערים: {gd_str}"
    )


def format_weekly_recap(recap_text: str, week_str: str) -> str:
    return (
        f"📅 *סיכום השבוע — {week_str}*\n\n"
        f"{recap_text}"
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
