import logging
from typing import Callable, Awaitable

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)

CommandReplyFn = Callable[[str], Awaitable[str]]


class TelegramNotifier:
    def __init__(self) -> None:
        self._bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self._chat_id = TELEGRAM_CHAT_ID
        self._app: Application | None = None
        self._command_handlers: dict[str, CommandReplyFn] = {}

    def register_command(self, name: str, handler: CommandReplyFn) -> None:
        """Register a /<name> command that calls handler(args_text) -> reply text."""
        self._command_handlers[name] = handler

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

    async def start_polling(self) -> None:
        """Start listening for slash-commands. Call once at startup."""
        if not self._command_handlers:
            return
        self._app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        for name, handler_fn in self._command_handlers.items():
            self._app.add_handler(CommandHandler(name, self._make_handler(handler_fn)))
        # Channel posts don't go through CommandHandler — register a separate
        # dispatcher that catches /commands posted in channels where the bot is admin.
        self._app.add_handler(MessageHandler(
            filters.UpdateType.CHANNEL_POST & filters.COMMAND,
            self._dispatch_channel_command,
        ))
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "channel_post"],
        )
        log.info("Telegram command polling started (%s)", list(self._command_handlers))

    def _make_handler(self, handler_fn: CommandReplyFn):
        async def _wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            args_text = " ".join(context.args) if context.args else ""
            try:
                reply = await handler_fn(args_text)
            except Exception:
                log.exception("Command handler crashed")
                reply = "שגיאה פנימית, נסה שוב מאוחר יותר."
            if update.effective_message:
                await update.effective_message.reply_text(
                    reply, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
                )
        return _wrapped

    async def _dispatch_channel_command(
        self, update: Update, _context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        post = update.channel_post
        if post is None or not post.text:
            return
        text = post.text.lstrip()
        if not text.startswith("/"):
            return
        parts = text[1:].split(maxsplit=1)
        if not parts:
            return
        cmd_name = parts[0].split("@", 1)[0].lower()
        args_text = parts[1] if len(parts) > 1 else ""
        handler_fn = self._command_handlers.get(cmd_name)
        if handler_fn is None:
            return
        try:
            reply = await handler_fn(args_text)
        except Exception:
            log.exception("Channel command handler crashed")
            reply = "שגיאה פנימית, נסה שוב מאוחר יותר."
        try:
            await post.reply_text(
                reply, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
            )
        except TelegramError:
            log.exception("Failed to reply to channel command")

    async def close(self) -> None:
        if self._app is None:
            return
        try:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        except Exception:
            log.exception("Error shutting down Telegram polling")
