"""Handlers for the Sora 2 invite flow."""

from __future__ import annotations

import logging

import db
from config import BOT_OWNER_ID
from modules.i18n import t
from telebot import TeleBot
from telebot.types import CallbackQuery

from utils import edit_or_send, ensure_force_sub
from .keyboards import main_keyboard, no_credit_keyboard
from .settings import CREDIT_COST, QUEUE_START_POSITION
from .texts import (
    admin_notification,
    intro,
    no_credit,
    no_credit_alert,
    purchase_success,
)

logger = logging.getLogger(__name__)


def _get_user_and_lang(from_user):
    user = db.get_or_create_user(from_user)
    db.touch_last_seen(user["user_id"])
    lang = db.get_user_lang(user["user_id"], "fa")
    return user, lang


def _notify_admin(bot: TeleBot, user: dict, position: int) -> None:
    if not BOT_OWNER_ID:
        return

    try:
        text = admin_notification(
            user_id=user.get("user_id"),
            username=(user.get("username") or ""),
            first_name=(user.get("first_name") or ""),
            credits=db.format_credit_amount(user.get("credits", 0)),
            position=position,
        )
        bot.send_message(BOT_OWNER_ID, text, parse_mode="HTML")
    except Exception as exc:
        logger.exception("Failed to notify admin about Sora 2 request", exc_info=exc)


def open_sora2_menu(bot: TeleBot, cq: CallbackQuery) -> None:
    user, lang = _get_user_and_lang(cq.from_user)
    if user.get("banned"):
        bot.answer_callback_query(cq.id, t("error_banned", lang), show_alert=True)
        return
    if not ensure_force_sub(bot, user["user_id"], cq.message.chat.id, cq.message.message_id, lang):
        bot.answer_callback_query(cq.id)
        return

    cost_text = db.format_credit_amount(CREDIT_COST)
    edit_or_send(
        bot,
        cq.message.chat.id,
        cq.message.message_id,
        intro(lang, cost=cost_text),
        main_keyboard(lang),
    )


def _handle_purchase(bot: TeleBot, cq: CallbackQuery) -> None:
    user, lang = _get_user_and_lang(cq.from_user)
    if user.get("banned"):
        bot.answer_callback_query(cq.id, t("error_banned", lang), show_alert=True)
        return
    if not ensure_force_sub(bot, user["user_id"], cq.message.chat.id, cq.message.message_id, lang):
        bot.answer_callback_query(cq.id)
        return

    fresh = db.get_user(user["user_id"]) or user
    credits_value = db.normalize_credit_amount(fresh.get("credits", 0))
    cost_text = db.format_credit_amount(CREDIT_COST)
    credits_text = db.format_credit_amount(credits_value)

    if credits_value < CREDIT_COST or not db.deduct_credits(user["user_id"], CREDIT_COST):
        edit_or_send(
            bot,
            cq.message.chat.id,
            cq.message.message_id,
            no_credit(lang, cost=cost_text, credits=credits_text),
            no_credit_keyboard(lang),
        )
        bot.answer_callback_query(cq.id, no_credit_alert(lang), show_alert=True)
        return

    queue_index = db.create_sora2_request(user["user_id"])
    position = max(QUEUE_START_POSITION, QUEUE_START_POSITION - 1 + queue_index)
    updated_user = db.get_user(user["user_id"]) or fresh

    edit_or_send(
        bot,
        cq.message.chat.id,
        cq.message.message_id,
        purchase_success(lang, cost=cost_text, position=position),
        main_keyboard(lang),
    )
    bot.answer_callback_query(cq.id)

    _notify_admin(bot, updated_user, position)


def register(bot: TeleBot) -> None:
    @bot.callback_query_handler(func=lambda c: c.data == "sora2:menu")
    def handle_menu(cq: CallbackQuery) -> None:
        bot.answer_callback_query(cq.id)
        open_sora2_menu(bot, cq)

    @bot.callback_query_handler(func=lambda c: c.data == "sora2:buy")
    def handle_buy(cq: CallbackQuery) -> None:
        _handle_purchase(bot, cq)
