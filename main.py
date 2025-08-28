# main.py
import os
import telebot
from config import BOT_TOKEN
from modules.home.handlers import register as home_register
from modules.tts.handlers import register as tts_register
from modules.profile.handlers import register as profile_register
from modules.credit.handlers import register as credit_register
from modules.invite.handlers import register as invite_register
from modules.admin.handlers import register as admin_register

bot = telebot.TeleBot(os.getenv("BOT_TOKEN", BOT_TOKEN), parse_mode="HTML")

# ثبت هندلرها
home_register(bot)
tts_register(bot)
profile_register(bot)
credit_register(bot)
invite_register(bot)
admin_register(bot)

if __name__ == "__main__":
    print("Vexa AI bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)