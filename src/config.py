import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {key}. "
            f"See .env.example and create a .env file."
        )
    return value


FOOTBALL_DATA_API_KEY = _require("FOOTBALL_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _require("TELEGRAM_CHAT_ID")
# Where ops/health alerts go (feed died, API down). Defaults to the main chat;
# set a private chat id to keep system messages off the public channel.
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID") or TELEGRAM_CHAT_ID
DISCORD_WEBHOOK_URL = _require("DISCORD_WEBHOOK_URL")
GROQ_API_KEY = _require("GROQ_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Durable state: when both are set, the bot stores state in Turso (cloud SQLite)
# instead of the local file, so dedup/sent flags survive Render restarts/deploys.
# When unset, falls back to the local SQLite file (current behavior).
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

ARSENAL_TEAM_ID = int(os.getenv("ARSENAL_TEAM_ID", "57"))
SPURS_TEAM_ID = int(os.getenv("SPURS_TEAM_ID", "73"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jerusalem")
MORNING_DIGEST_HOUR = int(os.getenv("MORNING_DIGEST_HOUR", "8"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def _flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# Set these to false when delegating to GitHub Actions
ENABLE_NEWS_POLLER = _flag("ENABLE_NEWS_POLLER", True)
ENABLE_MORNING_DIGEST = _flag("ENABLE_MORNING_DIGEST", True)
ENABLE_STANDINGS_ALERT = _flag("ENABLE_STANDINGS_ALERT", True)
ENABLE_WEEKLY_RECAP = _flag("ENABLE_WEEKLY_RECAP", True)

DB_PATH = ROOT_DIR / "data" / "state.db"
