# modules/invite/handlers.py
from __future__ import annotations

import time

from telebot import TeleBot
from telebot.types import CallbackQuery

import db
from modules.i18n import t
from utils import edit_or_send, ensure_force_sub
from .texts import INVITE_TEXT
from .keyboards import keyboard as invite_keyboard


DAILY_REWARD_AMOUNT = 10
DAILY_REWARD_INTERVAL = 24 * 60 * 60


def register(bot: TeleBot) -> None:
    @bot.callback_query_handler(func=lambda c: c.data in {"invite:daily_reward", "onboarding:daily_reward"})
    def handle_daily_reward(cq: CallbackQuery) -> None:
        user = db.get_or_create_user(cq.from_user)
        user_id = user["user_id"]
        lang = db.get_user_lang(user_id, "fa")

        if user.get("banned"):
            bot.answer_callback_query(cq.id, t("error_banned", lang), show_alert=True)
            return

        db.touch_last_seen(user_id)
        if not ensure_force_sub(bot, user_id, cq.message.chat.id, cq.message.message_id, lang):
            bot.answer_callback_query(cq.id)
            return

        _claim_daily_reward(bot, cq, user_id, lang)

    @bot.callback_query_handler(func=lambda c: c.data == "onboarding:invite")
    def handle_onboarding_invite(cq: CallbackQuery) -> None:
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        if user.get("banned"):
            bot.answer_callback_query(cq.id, t("error_banned", lang), show_alert=True)
            return

        db.touch_last_seen(user["user_id"])
        bot.answer_callback_query(cq.id)
        open_invite(bot, cq)

def open_invite(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    if not ensure_force_sub(bot, user["user_id"], cq.message.chat.id, cq.message.message_id, lang):
        return
    bonus = int(db.get_setting("BONUS_REFERRAL", "30") or 30)
    me = bot.get_me()
    ref_url = f"https://t.me/{me.username}?start={user['ref_code']}"
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, INVITE_TEXT(lang, ref_url, bonus), invite_keyboard(lang))


def open_invite_from_message(bot, msg, menu_message_id: int | None = None):
    user = db.get_or_create_user(msg.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    if not ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id, lang):
        return
    bonus = int(db.get_setting("BONUS_REFERRAL", "30") or 30)
    me = bot.get_me()
    ref_url = f"https://t.me/{me.username}?start={user['ref_code']}"
    if menu_message_id:
        edit_or_send(
            bot,
            msg.chat.id,
            menu_message_id,
            INVITE_TEXT(lang, ref_url, bonus),
            invite_keyboard(lang),
        )
    else:
        bot.send_message(
            msg.chat.id,
            INVITE_TEXT(lang, ref_url, bonus),
            reply_markup=invite_keyboard(lang),
            parse_mode="HTML",
        )


def _claim_daily_reward(bot: TeleBot, cq: CallbackQuery, user_id: int, lang: str) -> None:
    now = int(time.time())
    last_claim = db.get_last_daily_reward(user_id)
    if now - last_claim >= DAILY_REWARD_INTERVAL:
        db.add_credits(user_id, DAILY_REWARD_AMOUNT)
        db.set_last_daily_reward(user_id, now)
        amount_text = db.format_credit_amount(DAILY_REWARD_AMOUNT)
        bot.answer_callback_query(
            cq.id,
            t("invite_daily_reward_success", lang).format(amount=amount_text),
            show_alert=True,
        )
        return

    remaining = max(0, DAILY_REWARD_INTERVAL - (now - last_claim))
    remaining_text = _format_remaining_time(remaining)
    bot.answer_callback_query(
        cq.id,
        t("invite_daily_reward_cooldown", lang).format(time=remaining_text),
        show_alert=True,
    )


def _format_remaining_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"
