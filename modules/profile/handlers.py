# modules/profile/handlers.py
import db
from utils import edit_or_send, feature_disabled_text, is_feature_enabled, send_main_menu
from .texts import PROFILE_TEXT
from modules.home.keyboards import main_menu

def register(bot):
    pass

def open_profile(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    if not is_feature_enabled("FEATURE_PROFILE"):
        edit_or_send(
            bot,
            cq.message.chat.id,
            cq.message.message_id,
            feature_disabled_text("FEATURE_PROFILE", lang),
            main_menu(lang),
        )
        return
    txt = PROFILE_TEXT(lang, user["user_id"], user["credits"])
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, main_menu(lang))


def open_profile_from_message(bot, msg, menu_message_id: int | None = None):
    user = db.get_or_create_user(msg.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    if not is_feature_enabled("FEATURE_PROFILE"):
        if menu_message_id:
            send_main_menu(
                bot,
                user["user_id"],
                msg.chat.id,
                feature_disabled_text("FEATURE_PROFILE", lang),
                main_menu(lang),
                message_id=menu_message_id,
            )
        else:
            send_main_menu(
                bot,
                user["user_id"],
                msg.chat.id,
                feature_disabled_text("FEATURE_PROFILE", lang),
                main_menu(lang),
            )
        return
    txt = PROFILE_TEXT(lang, user["user_id"], user["credits"])
    if menu_message_id:
        send_main_menu(
            bot,
            user["user_id"],
            msg.chat.id,
            txt,
            main_menu(lang),
            message_id=menu_message_id,
        )
    else:
        send_main_menu(bot, user["user_id"], msg.chat.id, txt, main_menu(lang))
