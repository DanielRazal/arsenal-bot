import logging

from .client import LLMClient

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """אתה עורך חדשות ספורט בעברית עם מבט אוהד ארסנל.

קיבלת רשימה של כתבות שפורסמו ב-24 השעות האחרונות. תפקידך לבחור את 5 הנושאים החמים ביותר ולסכם אותם בקצרה לאוהד ארסנל בעברית.

כללים:
- בחר עד 5 נושאים. אם יש פחות כתבות, בחר פחות.
- אל תחזור על אותה כתבה פעמיים — אם כמה מקורות מדווחים על אותו דבר, אחד את הסיכום שלהם.
- לכל נושא: כותרת קצרה ב-bold, שורה-שתיים של הסבר בעברית, וקישור למקור (markdown).
- העדף חדשות העברה, פציעות, ראיונות, ותגובות אוהדים על פני סיכומי משחק שכבר היה לנו עליהם הודעה."""


async def make_digest(client: LLMClient, articles: list[dict]) -> str:
    if not articles:
        return "_אין כתבות חדשות מאז אתמול._"
    listing_lines = [
        f"- [{a['source']}] {a['title']} — {a.get('link', '')}"
        for a in articles
    ]
    user_msg = "הכתבות מהיממה האחרונה:\n\n" + "\n".join(listing_lines)
    try:
        return await client.complete(SYSTEM_PROMPT, user_msg, max_tokens=900)
    except Exception:
        log.exception("Digest generation failed")
        return "_(לא ניתן היה לחולל דייג'סט אוטומטי כרגע)_"
