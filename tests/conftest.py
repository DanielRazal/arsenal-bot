"""Test setup: provide dummy values for the required env vars so importing
src.config (which hard-fails on missing keys) works without a real .env or
secrets. Tests exercise pure logic and never make real API calls.
"""
import os

for _k in (
    "FOOTBALL_DATA_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "DISCORD_WEBHOOK_URL",
    "GROQ_API_KEY",
):
    os.environ.setdefault(_k, "test-value")
