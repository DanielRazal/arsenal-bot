import asyncio
import logging

from .base import Notifier
from .discord import DiscordNotifier
from .telegram import TelegramNotifier

log = logging.getLogger(__name__)


class Fanout:
    def __init__(self, notifiers: list[Notifier]) -> None:
        self._notifiers = notifiers

    @classmethod
    def default(cls) -> "Fanout":
        return cls([TelegramNotifier(), DiscordNotifier()])

    async def send(self, text: str) -> None:
        await asyncio.gather(
            *(n.send(text) for n in self._notifiers),
            return_exceptions=True,
        )

    async def close(self) -> None:
        await asyncio.gather(
            *(n.close() for n in self._notifiers),
            return_exceptions=True,
        )
