import json
import logging

from .client import LLMClient

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """אתה פרשן ספורט בעברית, אוהד ארסנל אדוק, עם חוש הומור ציני וסגנון דרמטי כמו פרשן רדיו ותיק.

תפקידך: לכתוב סיכום קצר ומלא אישיות של משחק ארסנל שהסתיים, על בסיס הנתונים שתקבל.

כללים:
- 4-6 שורות בלבד.
- התחל מהתוצאה בהקשר רגשי (חגיגי לניצחון, מר לתבוסה, ספקני לתיקו).
- הזכר את המבקיעים והדקות החשובות.
- צ'מצ'מ קצת על השופט / היריב / הכוכבים — אבל בטון משחק, לא רעיל.
- סיים בשורה חדה בסגנון "הלאה למשחק הבא".
- אסור לציין שאתה AI או "סיכום שנכתב על ידי...". פשוט תכתוב כפרשן."""


async def summarize_match(client: LLMClient, match: dict) -> str:
    raw = match.get("raw", {})
    payload = {
        "competition": match.get("competition"),
        "matchday": match.get("matchday"),
        "home_team": match["home_team"],
        "away_team": match["away_team"],
        "score": f"{match.get('score_home')}–{match.get('score_away')}",
        "goals": [
            {
                "minute": g.get("minute"),
                "scorer": (g.get("scorer") or {}).get("name"),
                "team": (g.get("team") or {}).get("name"),
                "type": g.get("type"),
            }
            for g in (raw.get("goals") or [])
        ],
        "bookings": [
            {
                "minute": b.get("minute"),
                "player": (b.get("player") or {}).get("name"),
                "team": (b.get("team") or {}).get("name"),
                "card": b.get("card"),
            }
            for b in (raw.get("bookings") or [])
        ],
    }
    user_msg = "סכם את המשחק הבא:\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        return await client.complete(SYSTEM_PROMPT, user_msg, max_tokens=400)
    except Exception:
        log.exception("Match summary generation failed; returning fallback")
        return "_(לא ניתן היה לחולל סיכום אוטומטי כרגע)_"
