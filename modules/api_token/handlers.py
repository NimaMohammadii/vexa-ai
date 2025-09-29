from __future__ import annotations

import db
from telebot import TeleBot
from telebot.types import CallbackQuery

from modules.i18n import t
from utils import edit_or_send

from .keyboards import token_menu
from .texts import render_token_message


def register(bot: TeleBot) -> None:
    """Register Telegram handlers for the API token menu."""

    @bot.callback_query_handler(func=lambda c: c.data == "home:api_token")
    def open_token_menu(cq: CallbackQuery) -> None:
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        if user.get("banned"):
            bot.answer_callback_query(cq.id, t("error_banned", lang), show_alert=True)
            return
        db.touch_last_seen(user["user_id"])
        token = db.get_or_create_api_token(user["user_id"])
        body = render_token_message(lang, token)
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, body, token_menu(lang))
        bot.answer_callback_query(cq.id)

    @bot.callback_query_handler(func=lambda c: c.data == "api:rotate")
    def rotate_token(cq: CallbackQuery) -> None:
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        if user.get("banned"):
            bot.answer_callback_query(cq.id, t("error_banned", lang), show_alert=True)
            return
        db.touch_last_seen(user["user_id"])
        token = db.rotate_api_token(user["user_id"])
        body = render_token_message(lang, token)
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, body, token_menu(lang))
        bot.answer_callback_query(cq.id, t("api_token_rotated", lang))
