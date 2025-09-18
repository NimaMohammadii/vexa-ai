# main.py
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import telebot
from config import BOT_TOKEN, DEBUG
import db

from modules.admin import handlers as admin_handlers
from modules.lang import handlers as lang_handlers   # ← جدید
from modules.home import handlers as home_handlers
from modules.tts import handlers as tts_handlers
from modules.profile import handlers as profile_handlers
from modules.credit import handlers as credit_handlers
from modules.invite import handlers as invite_handlers
from modules.clone import handlers as clone_handlers
from modules.gpt import handlers as gpt_handlers

def create_bot():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN در secrets تعریف نشده")
    return telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def register_modules(bot: telebot.TeleBot):
    admin_handlers.register(bot)
    lang_handlers.register(bot)     # ← جدید
    home_handlers.register(bot)
    tts_handlers.register(bot)
    profile_handlers.register(bot)
    credit_handlers.register(bot)
    invite_handlers.register(bot)
    clone_handlers.register(bot)
    gpt_handlers.register(bot)

if __name__ == "__main__":
    db.init_db()
    bot = create_bot()
    register_modules(bot)

    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    if DEBUG:
        print("✅ Bot started (DEBUG)")
        print(f"✅ Bot started (DEBUG) — HTTP server listening on 0.0.0.0:{port}")
    bot.infinity_polling(skip_pending=True, allowed_updates=["message","callback_query","pre_checkout_query","successful_payment"])
