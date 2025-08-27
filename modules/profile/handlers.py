# modules/profile/handlers.py
import db
from utils import edit_or_send
from .texts import PROFILE_TEXT
from modules.home.keyboards import main_menu

def register(bot):
    pass

def open_profile(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    txt = PROFILE_TEXT(lang, user["user_id"], user["credits"])
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, main_menu(lang))