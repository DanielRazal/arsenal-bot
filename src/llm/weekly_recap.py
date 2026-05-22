import json
import logging

from ..hebrew_names import hebrewize
from .client import LLMClient

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """אתה פרשן ספורט בעברית, אוהד ארסנל אדוק עם ניסיון של 20 שנה.
תפקידך לכתוב סיכום שבועי קצר ומרתק של כל מה שקרה עם ארסנל השבוע.

כללים:
- 6-10 שורות בלבד.
- כל הטקסט בעברית בלבד.
- פתח עם תוצאות המשחקים (אם היו).
- הזכר את עמדת הקבוצה בטבלה.
- אזכור של חדשות בולטות מהשבוע.
- סגנון חי, אישי, עם קצת הומור.
- סיים במשפט מוטיבציוני לקראת השבוע הבא.
- אסור לציין שאתה AI."""


async def make_weekly_recap(
    client: LLMClient,
    matches: list[dict],
    articles: list[dict],
    arsenal_row: dict | None,
) -> str:
    payload = {
        "matches": [
            {
                "competition": m.get("competition"),
                "home": m["home_team"],
                "away": m["away_team"],
                "score": f"{m.get('score_home')}–{m.get('score_away')}",
                "scorers": [
                    hebrewize((g.get("scorer") or {}).get("name", ""))
                    for g in (m.get("raw", {}).get("goals") or [])
                ],
            }
            for m in matches
        ],
        "standings": {
            "position": arsenal_row.get("position") if arsenal_row else None,
            "points": arsenal_row.get("points") if arsenal_row else None,
            "goal_difference": arsenal_row.get("goal_difference") if arsenal_row else None,
        },
        "news_headlines": [a.get("title", "") for a in articles[:12]],
    }
    user_msg = "סכם את השבוע של ארסנל:\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        return await client.complete(SYSTEM_PROMPT, user_msg, max_tokens=600)
    except Exception:
        log.exception("Weekly recap generation failed")
        return "_(לא ניתן היה לחולל סיכום שבועי אוטומטי)_"
