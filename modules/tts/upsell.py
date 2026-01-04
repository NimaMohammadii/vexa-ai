from __future__ import annotations

import threading
import time

import db
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from modules.i18n import t

CREATOR_UPSELL_DELAY = 20.0


def _creator_upgrade_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("tts_creator_upgrade_button", lang), callback_data="credit:stars"))
    return kb


def _send_creator_upsell(bot, user_id: int, chat_id: int) -> None:
    user = db.get_user(user_id)
    if not user or user.get("banned"):
        return
    if db.get_tts_creator_prompted_at(user_id) > 0:
        return
    lang = db.get_user_lang(user_id, "fa")
    try:
        bot.send_message(
            chat_id,
            t("tts_creator_upsell", lang),
            reply_markup=_creator_upgrade_keyboard(lang),
        )
    except Exception:
        return
    db.set_tts_creator_prompted_at(user_id, int(time.time()))


def schedule_creator_upsell(bot, user_id: int, chat_id: int) -> None:
    if db.get_tts_creator_prompted_at(user_id) > 0:
        return
    if db.count_tts_requests(user_id) != 1:
        return
    timer = threading.Timer(
        CREATOR_UPSELL_DELAY,
        _send_creator_upsell,
        args=(bot, user_id, chat_id),
    )
    timer.daemon = True
    timer.start()
