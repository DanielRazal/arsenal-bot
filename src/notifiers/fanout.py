import asyncio
import logging
from typing import Awaitable, Callable

from .base import Notifier
from .discord import DiscordNotifier
from .telegram import TelegramNotifier

log = logging.getLogger(__name__)

CommandReplyFn = Callable[[str], Awaitable[str]]


class Fanout:
    def __init__(self, notifiers: list[Notifier]) -> None:
        self._notifiers = notifiers
        self._telegram: TelegramNotifier | None = next(
            (n for n in notifiers if isinstance(n, TelegramNotifier)), None
        )

    @classmethod
    def default(cls) -> "Fanout":
        return cls([TelegramNotifier(), DiscordNotifier()])

    def register_telegram_command(self, name: str, handler: CommandReplyFn) -> None:
        if self._telegram is not None:
            self._telegram.register_command(name, handler)

    async def start(self) -> None:
        """Start any notifiers that need an async setup (e.g. Telegram polling)."""
        if self._telegram is not None:
            await self._telegram.start_polling()

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
