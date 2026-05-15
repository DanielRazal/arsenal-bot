import logging

import httpx

from ..config import DISCORD_WEBHOOK_URL

log = logging.getLogger(__name__)

DISCORD_MAX_LEN = 2000


class DiscordNotifier:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)
        self._webhook = DISCORD_WEBHOOK_URL

    async def send(self, text: str) -> None:
        # Discord uses its own markdown flavor — it mostly overlaps with Telegram's,
        # but Discord doesn't render single-* italics the same way. Keep it simple.
        chunks = [text[i:i + DISCORD_MAX_LEN] for i in range(0, len(text), DISCORD_MAX_LEN)] or [""]
        for chunk in chunks:
            try:
                resp = await self._client.post(self._webhook, json={"content": chunk})
                resp.raise_for_status()
            except httpx.HTTPError:
                log.exception("Discord send failed")
                return

    async def close(self) -> None:
        await self._client.aclose()
