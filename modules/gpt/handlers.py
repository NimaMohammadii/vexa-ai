from __future__ import annotations

"""Telegram handlers for GPT chat interactions."""

from typing import Optional

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

import db
from config import (
    DEBUG,
    GPT_API_KEY,
    GPT_HISTORY_LIMIT,
    GPT_SYSTEM_PROMPT,
)
from modules.i18n import t
from utils import check_force_sub, edit_or_send
from .service import (
    GPTServiceError,
    build_default_messages,
    chat_completion,
    extract_message_text,
)

GPT_STATE = "gpt:chat"


def _back_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _chat_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("gpt_new_chat", lang), callback_data="gpt:new"))
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _ensure_gpt_ready(lang: str) -> Optional[str]:
    if not GPT_API_KEY:
        return t("gpt_not_configured", lang)
    if not GPT_SYSTEM_PROMPT:
        return t("gpt_not_configured", lang)
    return None


def _respond(bot, status_message, lang: str, text: str) -> None:
    try:
        bot.edit_message_text(
            text,
            chat_id=status_message.chat.id,
            message_id=status_message.message_id,
            reply_markup=_chat_keyboard(lang),
            parse_mode=None,
        )
    except Exception:
        bot.send_message(
            status_message.chat.id,
            text,
            reply_markup=_chat_keyboard(lang),
            parse_mode=None,
        )


def _start_chat(bot, chat_id: int, message_id: int, user_id: int, lang: str) -> bool:
    error = _ensure_gpt_ready(lang)
    if error:
        edit_or_send(bot, chat_id, message_id, error, _back_keyboard(lang))
        return False

    db.set_state(user_id, GPT_STATE)
    text = t("gpt_open", lang)
    edit_or_send(bot, chat_id, message_id, text, _chat_keyboard(lang))
    return True


def _handle_force_sub(bot, user_id: int, lang: str, chat_id: int, message_id: int) -> bool:
    settings = db.get_settings()
    mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
    if mode not in ("new", "all"):
        return True
    ok, txt, kb = check_force_sub(bot, user_id, settings)
    if ok:
        return True
    edit_or_send(bot, chat_id, message_id, txt, kb)
    return False


def _load_history(user_id: int) -> list[dict[str, str]]:
    history = db.get_recent_gpt_messages(user_id, GPT_HISTORY_LIMIT)
    valid_history: list[dict[str, str]] = []
    for item in history:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role and content:
            valid_history.append({"role": role, "content": content})
    return valid_history


def register(bot):
    @bot.message_handler(commands=["gpt"])
    def open_gpt(msg):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است.")
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])
        if not _handle_force_sub(bot, user["user_id"], lang, msg.chat.id, msg.message_id):
            return

        _start_chat(bot, msg.chat.id, msg.message_id, user["user_id"], lang)

    @bot.message_handler(commands=["endgpt", "stopgpt"])
    def stop_gpt(msg):
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])
        db.clear_state(user["user_id"])
        db.clear_gpt_history(user["user_id"])
        bot.reply_to(msg, t("gpt_end", lang), reply_markup=_back_keyboard(lang))

    @bot.callback_query_handler(func=lambda c: c.data == "home:gpt_chat")
    def open_from_menu(cq):
        user = db.get_or_create_user(cq.from_user)
        if user.get("banned"):
            bot.answer_callback_query(cq.id, "⛔️")
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])
        if not _handle_force_sub(bot, user["user_id"], lang, cq.message.chat.id, cq.message.message_id):
            bot.answer_callback_query(cq.id)
            return

        if _start_chat(bot, cq.message.chat.id, cq.message.message_id, user["user_id"], lang):
            bot.answer_callback_query(cq.id)
        else:
            bot.answer_callback_query(cq.id, show_alert=True, text=t("gpt_not_configured_alert", lang))

    @bot.callback_query_handler(func=lambda c: c.data == "gpt:new")
    def reset_chat(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])
        db.clear_gpt_history(user["user_id"])
        db.set_state(user["user_id"], GPT_STATE)
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, t("gpt_reset", lang), _chat_keyboard(lang))
        bot.answer_callback_query(cq.id, text=t("gpt_reset_toast", lang), show_alert=False)

    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(GPT_STATE), content_types=["text"])
    def handle_chat(msg):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است.")
            return

        text = (msg.text or "").strip()
        if not text:
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        error = _ensure_gpt_ready(lang)
        if error:
            bot.reply_to(msg, error)
            db.clear_state(user["user_id"])
            return

        history = _load_history(user["user_id"])
        messages = build_default_messages(history, text)

        db.log_gpt_message(user["user_id"], "user", text)

        thinking = bot.send_message(msg.chat.id, t("gpt_wait", lang))

        try:
            data = chat_completion(messages)
            answer = (extract_message_text(data) or "").strip()
            if not answer:
                answer = t("gpt_empty", lang)
            db.log_gpt_message(user["user_id"], "assistant", answer)
            _respond(bot, thinking, lang, answer)
        except GPTServiceError as exc:
            _respond(bot, thinking, lang, t("gpt_error", lang).format(error=str(exc)))
        except Exception as exc:  # pragma: no cover - unexpected failure
            if DEBUG:
                print("GPT chat handler error:", exc)
            _respond(bot, thinking, lang, t("gpt_error", lang).format(error=t("gpt_error_unknown", lang)))
