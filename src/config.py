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
DISCORD_WEBHOOK_URL = _require("DISCORD_WEBHOOK_URL")
GROQ_API_KEY = _require("GROQ_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

ARSENAL_TEAM_ID = int(os.getenv("ARSENAL_TEAM_ID", "57"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jerusalem")
MORNING_DIGEST_HOUR = int(os.getenv("MORNING_DIGEST_HOUR", "8"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DB_PATH = ROOT_DIR / "data" / "state.db"
