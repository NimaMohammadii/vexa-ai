# modules/profile/handlers.py
import db
from .texts import PROFILE_ALERT_TEXT

def register(bot):
    pass

def open_profile(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    txt = PROFILE_ALERT_TEXT(lang, user["credits"])
    bot.answer_callback_query(cq.id, text=txt, show_alert=True)
