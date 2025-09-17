# modules/gpt/handlers.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import db
from modules.i18n import t
from utils import edit_or_send
from config import GPT_WEBAPP_URL


def _gpt_button(lang: str) -> InlineKeyboardButton:
    label = t("btn_gpt", lang)
    if GPT_WEBAPP_URL:
        return InlineKeyboardButton(label, web_app=WebAppInfo(GPT_WEBAPP_URL))
    return InlineKeyboardButton(label, callback_data="home:gpt_unavailable")


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "home:gpt_unavailable")
    def gpt_unavailable(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, t("gpt_unavailable", lang), kb)
        bot.answer_callback_query(cq.id, show_alert=True, text=t("gpt_unavailable_alert", lang))

    @bot.message_handler(commands=["gpt"])
    def open_gpt(msg):
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        kb = InlineKeyboardMarkup()
        kb.add(_gpt_button(lang))
        edit_or_send(bot, msg.chat.id, msg.message_id, t("gpt_open", lang), kb)