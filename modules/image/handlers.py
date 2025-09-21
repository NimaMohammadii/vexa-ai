"""Telegram handlers for the image generation flow."""

from __future__ import annotations

import time

from telebot.types import CallbackQuery, Message

import db
from config import DEBUG
from modules.home.keyboards import main_menu
from modules.home.texts import MAIN
from utils import check_force_sub, edit_or_send

from .keyboards import menu_keyboard, no_credit_keyboard
from .service import ImageGenerationError, generate_image, is_configured
from .settings import CREDIT_COST, STATE_PROCESSING, STATE_WAIT_PROMPT
from .texts import error, intro, no_credit, not_configured, processing, result_caption


def open_image(bot, cq: CallbackQuery) -> None:
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")

    if not is_configured():
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, not_configured(lang), menu_keyboard(lang))
        db.clear_state(user["user_id"])
        return

    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, intro(lang), menu_keyboard(lang))
    db.set_state(user["user_id"], STATE_WAIT_PROMPT)


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "image:back")
    def on_back(cq: CallbackQuery):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        db.clear_state(user["user_id"])
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
        bot.answer_callback_query(cq.id)

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_PROMPT),
        content_types=["text"],
    )
    def on_prompt(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        user_id = user["user_id"]
        lang = db.get_user_lang(user_id, "fa")

        prompt = (msg.text or "").strip()
        if not prompt:
            return

        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user_id, settings, lang)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb)
                return

        if not is_configured():
            bot.send_message(msg.chat.id, not_configured(lang), reply_markup=menu_keyboard(lang))
            db.clear_state(user_id)
            return

        if not db.deduct_credits(user_id, CREDIT_COST):
            refreshed = db.get_user(user_id) or {}
            credits = int(refreshed.get("credits") or 0)
            bot.send_message(msg.chat.id, no_credit(lang, credits), reply_markup=no_credit_keyboard(lang))
            db.set_state(user_id, STATE_WAIT_PROMPT)
            return

        db.set_state(user_id, f"{STATE_PROCESSING}:{int(time.time())}")
        status = bot.send_message(msg.chat.id, processing(lang))

        try:
            image_bytes = generate_image(prompt)
        except ImageGenerationError as exc:
            db.add_credits(user_id, CREDIT_COST)
            if DEBUG:
                print(f"[Runway] generation failed: {exc}", flush=True)
            _notify_error(bot, status, lang)
            db.set_state(user_id, STATE_WAIT_PROMPT)
            return
        except Exception as exc:  # pragma: no cover - safety net
            db.add_credits(user_id, CREDIT_COST)
            if DEBUG:
                print(f"[Runway] unexpected error: {exc}", flush=True)
            _notify_error(bot, status, lang)
            db.set_state(user_id, STATE_WAIT_PROMPT)
            return

        try:
            bot.delete_message(status.chat.id, status.message_id)
        except Exception:
            pass

        bot.send_photo(msg.chat.id, image_bytes, caption=result_caption(lang))
        db.set_state(user_id, STATE_WAIT_PROMPT)
        bot.send_message(msg.chat.id, intro(lang), reply_markup=menu_keyboard(lang))


def _notify_error(bot, status_message: Message, lang: str) -> None:
    try:
        bot.edit_message_text(error(lang), status_message.chat.id, status_message.message_id)
    except Exception:
        bot.send_message(status_message.chat.id, error(lang))
