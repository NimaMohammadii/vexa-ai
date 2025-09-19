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
    GPT_MESSAGE_COST,
    GPT_RESPONSE_CHAR_LIMIT,
)
from modules.i18n import t
from utils import check_force_sub, edit_or_send
from modules.home.keyboards import main_menu
from modules.home.texts import MAIN
from .service import (
    GPTServiceError,
    build_default_messages,
    chat_completion,
    extract_message_text,
    resolve_gpt_api_key,
    web_search,
)

GPT_STATE = "gpt:chat"
GPT_SEARCH_STATE = "gpt:search"


def _back_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _chat_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(t("gpt_new_chat", lang), callback_data="gpt:new"),
        InlineKeyboardButton(t("gpt_search", lang), callback_data="gpt:search"),
    )
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _ensure_gpt_ready(lang: str) -> Optional[str]:
    if not (GPT_API_KEY or resolve_gpt_api_key()):
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


def _format_credits(value: float) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "0"
    if abs(num - round(num)) < 0.01:
        return str(int(round(num)))
    return f"{num:.1f}".rstrip("0").rstrip(".")


def _send_no_credit(bot, chat_id: int, lang: str, balance: float) -> None:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"))
    text = t("gpt_no_credit", lang).format(
        cost=_format_credits(GPT_MESSAGE_COST),
        balance=_format_credits(balance),
    )
    bot.send_message(chat_id, text, reply_markup=kb)


def _charge_for_message(bot, user_id: int, chat_id: int, lang: str) -> bool:
    if db.deduct_credits(user_id, GPT_MESSAGE_COST):
        return True
    refreshed = db.get_user(user_id)
    balance = (refreshed or {}).get("credits", 0)
    _send_no_credit(bot, chat_id, lang, balance)
    return False


def _trim_answer(answer: str) -> str:
    limit = max(0, int(GPT_RESPONSE_CHAR_LIMIT))
    if limit and len(answer) > limit:
        trimmed = answer[:limit].rstrip()
        if not trimmed.endswith("…"):
            trimmed = f"{trimmed}…"
        return trimmed
    return answer


def _finish_chat(bot, chat_id: int, message_id: int, user_id: int, lang: str) -> None:
    db.clear_state(user_id)
    db.clear_gpt_history(user_id)
    text = f"{t('gpt_end', lang)}\n\n{MAIN(lang)}"
    edit_or_send(bot, chat_id, message_id, text, main_menu(lang))


def _start_chat(bot, chat_id: int, message_id: int, user_id: int, lang: str) -> bool:
    error = _ensure_gpt_ready(lang)
    if error:
        edit_or_send(bot, chat_id, message_id, error, _back_keyboard(lang))
        return False

    db.set_state(user_id, GPT_STATE)
    text = t("gpt_open", lang).format(cost=_format_credits(GPT_MESSAGE_COST))
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


def _build_search_context(query: str, results: list[dict[str, str]]) -> str:
    base = [f"Web search results for query: {query}"]
    if not results:
        base.append("No additional sources were found.")
    else:
        for idx, item in enumerate(results, 1):
            title = (item.get("title") or "").strip()
            snippet = (item.get("snippet") or "").strip()
            url = (item.get("url") or "").strip()
            summary_parts = []
            if title:
                summary_parts.append(title)
            if snippet:
                summary_parts.append(snippet[:220])
            line = f"{idx}. {' — '.join(summary_parts) if summary_parts else 'Result'}"
            if url:
                line = f"{line} ({url})"
            base.append(line)
    base.append("Use the available information to answer the user accurately.")
    return "\n".join(base)


def _handle_chat_completion(bot, user_id: int, chat_id: int, lang: str, messages, thinking):
    try:
        data = chat_completion(messages)
        answer = (extract_message_text(data) or "").strip()
        if not answer:
            answer = t("gpt_empty", lang)
        answer = _trim_answer(answer)
        db.log_gpt_message(user_id, "assistant", answer)
        _respond(bot, thinking, lang, answer)
    except GPTServiceError as exc:
        _respond(bot, thinking, lang, t("gpt_error", lang).format(error=str(exc)))
    except Exception as exc:  # pragma: no cover - unexpected failure
        if DEBUG:
            print("GPT chat handler error:", exc)
        _respond(bot, thinking, lang, t("gpt_error", lang).format(error=t("gpt_error_unknown", lang)))


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

        state = db.get_state(user["user_id"]) or ""
        if state.startswith("gpt:"):
            _finish_chat(bot, msg.chat.id, msg.message_id, user["user_id"], lang)
        else:
            _start_chat(bot, msg.chat.id, msg.message_id, user["user_id"], lang)

    @bot.message_handler(commands=["endgpt", "stopgpt"])
    def stop_gpt(msg):
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])
        _finish_chat(bot, msg.chat.id, msg.message_id, user["user_id"], lang)

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

        current_state = db.get_state(user["user_id"]) or ""
        if current_state.startswith("gpt:"):
            _finish_chat(bot, cq.message.chat.id, cq.message.message_id, user["user_id"], lang)
            bot.answer_callback_query(cq.id, text=t("gpt_end", lang), show_alert=False)
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

    @bot.callback_query_handler(func=lambda c: c.data == "gpt:search")
    def start_search(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])
        db.set_state(user["user_id"], GPT_SEARCH_STATE)
        prompt = t("gpt_search_prompt", lang).format(cost=_format_credits(GPT_MESSAGE_COST))
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, prompt, _chat_keyboard(lang))
        bot.answer_callback_query(cq.id)

    def _is_gpt_message(message) -> bool:
        state = db.get_state(message.from_user.id) or ""
        return state.startswith("gpt:")

    @bot.message_handler(func=_is_gpt_message, content_types=["text"])
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

        state = db.get_state(user["user_id"]) or ""

        if state == GPT_SEARCH_STATE:
            if not _charge_for_message(bot, user["user_id"], msg.chat.id, lang):
                db.set_state(user["user_id"], GPT_STATE)
                return

            history = _load_history(user["user_id"])
            try:
                results = web_search(text, max_results=3)
            except GPTServiceError as exc:
                results = []
                if DEBUG:
                    print("Web search error:", exc)
            search_context = _build_search_context(text, results)
            messages = build_default_messages(history, text)
            messages.insert(-1, {"role": "system", "content": search_context})

            db.log_gpt_message(user["user_id"], "user", f"[search] {text}")

            thinking = bot.send_message(msg.chat.id, t("gpt_wait", lang))
            _handle_chat_completion(bot, user["user_id"], msg.chat.id, lang, messages, thinking)
            db.set_state(user["user_id"], GPT_STATE)
            return

        if not _charge_for_message(bot, user["user_id"], msg.chat.id, lang):
            return

        history = _load_history(user["user_id"])
        messages = build_default_messages(history, text)

        db.log_gpt_message(user["user_id"], "user", text)

        thinking = bot.send_message(msg.chat.id, t("gpt_wait", lang))
        _handle_chat_completion(bot, user["user_id"], msg.chat.id, lang, messages, thinking)
