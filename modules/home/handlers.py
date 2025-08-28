# modules/home/handlers.py
import db
from utils import edit_or_send, check_force_sub
from .texts import MAIN
from .keyboards import main_menu

def register(bot):
    @bot.message_handler(commands=['start'])
    def start(msg):
        user = db.get_or_create_user(msg.from_user)
        db.touch_last_seen(user["user_id"])
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است."); return

        # Force-Sub در صورت فعال بودن
        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb); return

        # اگر رفرال داری، همین‌جا هندل کن (نسخه فعلی شما)
        try:
            from modules.home.referral import handle_referral
            handle_referral(bot, msg, user)
        except Exception:
            pass

        # منوی اصلی فارسی
        edit_or_send(bot, msg.chat.id, msg.message_id, MAIN("fa"), main_menu("fa"))

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("home:"))
    def home_router(cq):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])

        route = cq.data.split(":", 1)[1]

        if route == "back":
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN("fa"), main_menu("fa"))
            return

        if route == "tts":
            bot.answer_callback_query(cq.id)
            from modules.tts.handlers import open_tts
            open_tts(bot, cq); return

        if route == "profile":
            bot.answer_callback_query(cq.id)
            from modules.profile.handlers import open_profile
            open_profile(bot, cq); return

        if route == "credit":
            bot.answer_callback_query(cq.id)
            from modules.credit.handlers import open_credit
            open_credit(bot, cq); return

        if route == "invite":
            bot.answer_callback_query(cq.id)
            from modules.invite.handlers import open_invite
            open_invite(bot, cq); return