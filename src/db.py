import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    utc_date TEXT,
    status TEXT,
    home_team TEXT,
    away_team TEXT,
    score_home INTEGER,
    score_away INTEGER,
    summary_sent INTEGER DEFAULT 0,
    prematch_alert_sent INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS match_events (
    match_id INTEGER,
    event_id TEXT,
    sent_at TEXT,
    PRIMARY KEY (match_id, event_id)
);

CREATE TABLE IF NOT EXISTS articles (
    link TEXT PRIMARY KEY,
    source TEXT,
    title TEXT,
    summary TEXT,
    published_at TEXT,
    seen_at TEXT,
    sent_individually INTEGER DEFAULT 0,
    included_in_digest INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_seen_at ON articles(seen_at);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
"""


def init_db(path: Path = DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn(path: Path = DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_match(match: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO matches (id, utc_date, status, home_team, away_team, score_home, score_away)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                score_home=excluded.score_home,
                score_away=excluded.score_away
            """,
            (
                match["id"],
                match["utc_date"],
                match["status"],
                match["home_team"],
                match["away_team"],
                match.get("score_home"),
                match.get("score_away"),
            ),
        )


def event_already_sent(match_id: int, event_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM match_events WHERE match_id=? AND event_id=?",
            (match_id, event_id),
        ).fetchone()
        return row is not None


def mark_event_sent(match_id: int, event_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO match_events (match_id, event_id, sent_at) VALUES (?, ?, ?)",
            (match_id, event_id, now_iso()),
        )


def mark_summary_sent(match_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE matches SET summary_sent=1 WHERE id=?", (match_id,))


def mark_prematch_sent(match_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE matches SET prematch_alert_sent=1 WHERE id=?", (match_id,))


def match_needs_summary(match_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT summary_sent FROM matches WHERE id=?", (match_id,)
        ).fetchone()
        return row is not None and row["summary_sent"] == 0


def insert_article_if_new(link: str, source: str, title: str, summary: str, published_at: str) -> bool:
    """Returns True if the article was new (inserted), False if duplicate."""
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO articles (link, source, title, summary, published_at, seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (link, source, title, summary, published_at, now_iso()),
        )
        return cursor.rowcount > 0


def mark_article_sent(link: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE articles SET sent_individually=1 WHERE link=?", (link,))


def get_articles_for_digest(since_iso: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT link, source, title, summary, published_at
            FROM articles
            WHERE seen_at >= ? AND included_in_digest = 0
            ORDER BY seen_at DESC
            """,
            (since_iso,),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_articles_in_digest(links: list[str]) -> None:
    if not links:
        return
    placeholders = ",".join("?" * len(links))
    with get_conn() as conn:
        conn.execute(
            f"UPDATE articles SET included_in_digest=1 WHERE link IN ({placeholders})",
            links,
        )
