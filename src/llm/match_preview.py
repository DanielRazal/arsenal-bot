import json
import logging

from ..config import ARSENAL_TEAM_ID
from ..hebrew_names import hebrewize, hebrewize_competition, hebrewize_team
from .client import LLMClient

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """אתה פרשן ספורט בעברית, אוהד ארסנל אדוק, עם סגנון דרמטי ומלא ציפייה כמו פרשן רדיו לפני משחק גדול.

תפקידך: לכתוב תצוגה מקדימה קצרה לקראת משחק ארסנל שעומד להתחיל, על בסיס הנתונים שתקבל.

כללים:
- 3-5 שורות בלבד.
- כל הטקסט בעברית בלבד. השמות בנתונים כבר בעברית — השתמש בהם בדיוק כפי שהם.
- התייחס ליריבה, לכושר האחרון של ארסנל, ולמה לצפות מהמשחק.
- טון של ציפייה והתלהבות, עם קורט הומור.
- אל תמציא תוצאות או הרכבים — רק על בסיס הנתונים.
- אל תציין שאתה AI. פשוט תכתוב כפרשן."""


def _form_line(m: dict) -> str:
    arsenal_home = m.get("home_team_id") == ARSENAL_TEAM_ID
    ars = (m.get("score_home") if arsenal_home else m.get("score_away")) or 0
    opp = (m.get("score_away") if arsenal_home else m.get("score_home")) or 0
    opp_name = hebrewize_team(m.get("away_team") if arsenal_home else m.get("home_team"))
    verdict = "ניצחון" if ars > opp else ("תיקו" if ars == opp else "הפסד")
    return f"{verdict} {ars}-{opp} מול {opp_name}"


async def make_preview(client: LLMClient, match: dict, recent_results: list[dict]) -> str:
    payload = {
        "competition": hebrewize_competition(match.get("competition") or ""),
        "home_team": hebrewize_team(match.get("home_team", "")),
        "away_team": hebrewize_team(match.get("away_team", "")),
        "arsenal_recent_form": [_form_line(m) for m in recent_results[:5]],
    }
    user_msg = "כתוב תצוגה מקדימה למשחק הבא:\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        return hebrewize(await client.complete(SYSTEM_PROMPT, user_msg, max_tokens=350))
    except Exception:
        log.exception("Match preview generation failed")
        return ""
