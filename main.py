"""Entry point for the Vexa AI Telegram bot."""
from __future__ import annotations

import telebot

from config import BOT_TOKEN
import db

# ---- Telegram modules ----
from modules.admin import handlers as admin_handlers
from modules.home import handlers as home_handlers
from modules.invite import handlers as invite_handlers
from modules.lang import handlers as lang_handlers
from modules.profile import handlers as profile_handlers
from modules.credit import handlers as credit_handlers
from modules.clone import handlers as clone_handlers
from modules.tts import handlers as tts_handlers
from modules.tts_openai import handlers as tts_openai_handlers
from modules.gpt import handlers as gpt_handlers
from modules.anonymous_chat import handlers as anonymous_chat_handlers
from modules.image import handlers as image_handlers
from modules.video_gen4 import handlers as video_handlers
from modules.api_token import handlers as api_token_handlers
from modules.vexa_assistant import handlers as vexa_assistant_handlers

# ========================= Telegram Bot Wiring =========================
def create_bot() -> telebot.TeleBot:
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN در secrets تعریف نشده")
    return telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def register_modules(bot: telebot.TeleBot) -> None:
    admin_handlers.register(bot)
    lang_handlers.register(bot)
    home_handlers.register(bot)
    invite_handlers.register(bot)
    profile_handlers.register(bot)
    credit_handlers.register (bot)
    clone_handlers.register(bot)
    tts_handlers.register(bot)
    tts_openai_handlers.register(bot)
    vexa_assistant_handlers.register(bot)
    gpt_handlers.register(bot)
    anonymous_chat_handlers.register(bot)
    image_handlers.register(bot)
    video_handlers.register(bot)
    api_token_handlers.register(bot)

def main() -> None:
    db.init_db()
    bot = create_bot()
    register_modules(bot)

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=["message", "callback_query", "pre_checkout_query", "successful_payment"],
    )

if __name__ == "__main__":
    main()
