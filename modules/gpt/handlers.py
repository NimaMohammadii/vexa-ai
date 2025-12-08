from __future__ import annotations

"""Telegram handlers for GPT chat interactions."""

from typing import Optional

import html
import base64
import mimetypes

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

import db
from config import (
    DEBUG,
    GPT_API_KEY,
    GPT_HISTORY_LIMIT,
    GPT_SYSTEM_PROMPT,
    GPT_MESSAGE_COST,
    GPT_SEARCH_MESSAGE_COST,
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

PRICE_KEYWORDS = {
    "قیمت",
    "چنده",
    "چند است",
    "چند شد",
    "نرخ",
    "rate",
    "price",
    "cost",
    "how much",
    "worth",
}

TREND_KEYWORDS = {
    "btc",
    "bitcoin",
    "eth",
    "ethereum",
    "طلا",
    "دلار",
    "یورو",
    "تتر",
    "usdt",
    "سکه",
    "بورس",
    "stock",
    "سهام",
    "ارز",
    "crypto",
}

REALTIME_HINTS = {
    "امروز",
    "الان",
    "جدید",
    "امروزی",
    "latest",
    "today",
    "now",
    "current",
    "price",
    "قیمت",
}


def _back_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _chat_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _ensure_gpt_ready(lang: str) -> Optional[str]:
    if not (GPT_API_KEY or resolve_gpt_api_key()):
        return t("gpt_not_configured", lang)
    if not GPT_SYSTEM_PROMPT:
        return t("gpt_not_configured", lang)
    return None


def _respond(bot, status_message, lang: str, text: str, reply_markup=None) -> None:
    safe_text = text if ("<" in text or ">" in text) else html.escape(text)
    kb = reply_markup
    try:
        bot.edit_message_text(
            safe_text,
            chat_id=status_message.chat.id,
            message_id=status_message.message_id,
            reply_markup=kb,
            parse_mode="HTML",
        )
    except Exception:
        bot.send_message(
            status_message.chat.id,
            safe_text,
            reply_markup=kb,
            parse_mode="HTML",
        )


def _format_credits(value: float) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "0"
    if abs(num - round(num)) < 0.01:
        return str(int(round(num)))
    return f"{num:.1f}".rstrip("0").rstrip(".")


def _send_no_credit(bot, chat_id: int, lang: str, balance: float, cost: float) -> None:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"))
    text = t("gpt_no_credit", lang).format(
        cost=_format_credits(cost),
        balance=_format_credits(balance),
    )
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")


def _charge_for_message(bot, user_id: int, chat_id: int, lang: str, cost: float) -> bool:
    if db.deduct_credits(user_id, cost):
        return True
    refreshed = db.get_user(user_id)
    balance = (refreshed or {}).get("credits", 0)
    _send_no_credit(bot, chat_id, lang, balance, cost)
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


def _guess_mime_type(file_path: str, fallback: str = "image/jpeg") -> str:
    mime, _ = mimetypes.guess_type(file_path)
    return mime or fallback


def _download_file(bot, file_id: str) -> tuple[bytes, str | None]:
    file_path: str | None = None

    try:
        file_info = bot.get_file(file_id)
        file_path = getattr(file_info, "file_path", None)
    except Exception:
        file_info = None

    content: bytes | None = None

    if file_path:
        try:
            content = bot.download_file(file_path)
        except Exception:
            content = None

    if content is None:
        download_by_id = getattr(bot, "download_file_by_id", None)
        if callable(download_by_id):
            try:
                content = download_by_id(file_id)
            except Exception:
                content = None

    if not content:
        raise RuntimeError("empty file content")

    return content, file_path


def _extract_image_data(bot, message) -> tuple[str, str]:
    if getattr(message, "photo", None):
        photo = message.photo[-1]
        content, file_path = _download_file(bot, photo.file_id)
        mime = _guess_mime_type(file_path or "")
    elif getattr(message, "document", None):
        doc = message.document
        mime = (getattr(doc, "mime_type", "") or "").lower()
        if mime and not mime.startswith("image/"):
            raise ValueError("unsupported")
        content, file_path = _download_file(bot, doc.file_id)
        if not mime:
            mime = _guess_mime_type(file_path or "")
        if not mime.startswith("image/"):
            raise ValueError("unsupported")
    else:
        raise ValueError("no image")

    data_url = f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"
    return data_url, mime


def _start_chat(
    bot,
    chat_id: int,
    message_id: int,
    user_id: int,
    lang: str,
    *,
    reset_history: bool = True,
) -> bool:
    error = _ensure_gpt_ready(lang)
    if error:
        edit_or_send(bot, chat_id, message_id, error, _back_keyboard(lang))
        return False

    db.set_state(user_id, GPT_STATE)
    if reset_history:
        db.clear_gpt_history(user_id)
    text = t("gpt_open", lang).format(cost=_format_credits(GPT_MESSAGE_COST))
    edit_or_send(bot, chat_id, message_id, text, _chat_keyboard(lang))
    return True


def _process_search_query(bot, user_id: int, chat_id: int, lang: str, query: str) -> None:
    text = (query or "").strip()
    if not text:
        return

    if not _charge_for_message(bot, user_id, chat_id, lang, GPT_SEARCH_MESSAGE_COST):
        db.set_state(user_id, GPT_STATE)
        return

    history = _load_history(user_id)
    try:
        results = web_search(text, max_results=3)
    except GPTServiceError as exc:
        db.set_state(user_id, GPT_STATE)
        error_html = t("gpt_search_error", lang).format(error=html.escape(str(exc)))
        bot.send_message(chat_id, error_html, parse_mode="HTML")
        return

    if not results:
        bot.send_message(chat_id, t("gpt_search_no_results", lang), parse_mode="HTML")

    search_context = _build_search_context(text, results)
    messages = build_default_messages(history, text)
    messages.insert(-1, {"role": "system", "content": search_context})

    db.log_gpt_message(user_id, "user", f"[search] {text}")

    thinking = bot.send_message(chat_id, t("gpt_wait", lang), parse_mode="HTML")
    _handle_chat_completion(bot, user_id, chat_id, lang, messages, thinking)
    db.set_state(user_id, GPT_STATE)


def _should_use_search(text: str) -> bool:
    normalized = (text or "").lower()
    normalized = normalized.replace("؟", "?")
    if any(keyword in normalized for keyword in PRICE_KEYWORDS):
        return True
    if any(keyword in normalized for keyword in TREND_KEYWORDS):
        if "?" in normalized or any(hint in normalized for hint in REALTIME_HINTS):
            return True
    return False


def _handle_force_sub(bot, user_id: int, lang: str, chat_id: int, message_id: int) -> bool:
    settings = db.get_settings()
    mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
    if mode not in ("new", "all"):
        return True
    ok, txt, kb = check_force_sub(bot, user_id, settings, lang)
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
        _respond(bot, thinking, lang, t("gpt_error", lang).format(error=html.escape(str(exc))))
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

        _start_chat(bot, msg.chat.id, msg.message_id, user["user_id"], lang, reset_history=True)

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

        if _start_chat(bot, cq.message.chat.id, cq.message.message_id, user["user_id"], lang, reset_history=True):
            bot.answer_callback_query(cq.id)
        else:
            bot.answer_callback_query(cq.id, show_alert=True, text=t("gpt_not_configured_alert", lang))

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
            bot.reply_to(msg, error, parse_mode="HTML")
            db.clear_state(user["user_id"])
            return

        if _should_use_search(text):
            _process_search_query(bot, user["user_id"], msg.chat.id, lang, text)
            return

        if not _charge_for_message(bot, user["user_id"], msg.chat.id, lang, GPT_MESSAGE_COST):
            return

        history = _load_history(user["user_id"])
        messages = build_default_messages(history, text)

        db.log_gpt_message(user["user_id"], "user", text)

        thinking = bot.send_message(msg.chat.id, t("gpt_wait", lang), parse_mode="HTML")
        _handle_chat_completion(bot, user["user_id"], msg.chat.id, lang, messages, thinking)

    @bot.message_handler(func=_is_gpt_message, content_types=["photo", "document"])
    def handle_image(msg):
        if DEBUG:
            print(f"[GPT Image Handler] Received image from user {msg.from_user.id}, caption: {msg.caption}")
        
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است.")
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        error = _ensure_gpt_ready(lang)
        if error:
            bot.reply_to(msg, error, parse_mode="HTML")
            db.clear_state(user["user_id"])
            return

        try:
            image_url, _ = _extract_image_data(bot, msg)
            if DEBUG:
                print(f"[GPT Image Handler] Image extracted, URL length: {len(image_url)}")
        except ValueError as e:
            if DEBUG:
                print(f"[GPT Image Handler] ValueError: {e}")
            bot.reply_to(msg, t("gpt_image_unsupported", lang), parse_mode="HTML")
            return
        except Exception as e:
            if DEBUG:
                print(f"[GPT Image Handler] Exception: {e}")
            bot.reply_to(msg, t("gpt_image_download_error", lang), parse_mode="HTML")
            return

        if not _charge_for_message(bot, user["user_id"], msg.chat.id, lang, GPT_MESSAGE_COST):
            return

        instructions = (msg.caption or "").strip() or t("gpt_image_default_prompt", lang)

        history = _load_history(user["user_id"])
        messages = build_default_messages(history, instructions)
        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": instructions},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }

        db.log_gpt_message(user["user_id"], "user", f"[image] {instructions}")

        thinking = bot.send_message(msg.chat.id, t("gpt_wait", lang), parse_mode="HTML")
        _handle_chat_completion(bot, user["user_id"], msg.chat.id, lang, messages, thinking)
