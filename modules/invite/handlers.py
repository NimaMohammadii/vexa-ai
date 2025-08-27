# modules/invite/handlers.py
import db
from utils import edit_or_send
from .texts import INVITE_TEXT
from .keyboards import keyboard as invite_keyboard

def register(bot):
    pass

def open_invite(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    bonus = int(db.get_setting("BONUS_REFERRAL", "30") or 30)
    me = bot.get_me()
    ref_url = f"https://t.me/{me.username}?start={user['ref_code']}"
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, INVITE_TEXT(lang, ref_url, bonus), invite_keyboard(lang))