import logging

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        self._bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self._chat_id = TELEGRAM_CHAT_ID

    async def send(self, text: str) -> None:
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
        except TelegramError:
            log.exception("Telegram send failed")

    async def close(self) -> None:
        pass
