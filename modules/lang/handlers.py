# modules/lang/handlers.py
import db
from utils import edit_or_send
from .texts import TITLE
from .keyboards import lang_menu
from modules.home.texts import MAIN
from modules.home.keyboards import main_menu
from modules.i18n import t


def _send_language_menu(bot, user, chat_id, message_id):
    lang = db.get_user_lang(user["user_id"], "fa")
    edit_or_send(bot, chat_id, message_id, TITLE(lang), lang_menu(lang, lang))


def register(bot):
    @bot.message_handler(commands=["language"])
    def language_cmd(msg):
        user = db.get_or_create_user(msg.from_user)
        _send_language_menu(bot, user, msg.chat.id, msg.message_id)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("lang:"))
    def lang_router(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        parts = cq.data.split(":")
        action = parts[1]

        if action == "back":
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
            return

        if action == "set":
            code = parts[2]
            db.set_user_lang(user["user_id"], code)
            lang = code
            bot.answer_callback_query(cq.id, t("lang_saved", lang))
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
            return


def open_language(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    _send_language_menu(bot, user, cq.message.chat.id, cq.message.message_id)
