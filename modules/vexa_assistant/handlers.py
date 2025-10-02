"""Telegram handlers for the dedicated Vexa Assistant menu."""

from __future__ import annotations

import base64
import html
import mimetypes

from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import VEXA_ASSISTANT_HISTORY_LIMIT, VEXA_ASSISTANT_MESSAGE_COST
from modules.home.keyboards import main_menu
from modules.home.texts import MAIN
from modules.i18n import t
from utils import check_force_sub, edit_or_send

from .service import VexaAssistantError, ensure_ready, request_response

STATE = "vexa_assistant:chat"


def _format_amount(value: float) -> str:
    try:
        return db.format_credit_amount(value)
    except Exception:
        return str(value)


def _back_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _chat_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def _ensure_ready(lang: str) -> str | None:
    ok, error = ensure_ready()
    if ok:
        return None
    if error in {"missing_api_key"}:
        return t("vexa_assistant_not_configured", lang)
    return t("vexa_assistant_error", lang).format(error=html.escape(str(error)))


def _ensure_force_sub(bot, user_id: int, chat_id: int, message_id: int, lang: str) -> bool:
    settings = db.get_settings()
    mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
    if mode not in ("new", "all"):
        return True
    ok, txt, kb = check_force_sub(bot, user_id, settings, lang)
    if ok:
        return True
    edit_or_send(bot, chat_id, message_id, txt, kb)
    return False


def _charge_for_message(bot, user_id: int, chat_id: int, lang: str, cost: float) -> bool:
    if cost <= 0:
        return True

    if db.deduct_credits(user_id, cost):
        return True

    refreshed = db.get_user(user_id)
    balance = (refreshed or {}).get("credits", 0)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"))
    text = t("vexa_assistant_no_credit", lang).format(
        cost=_format_amount(cost),
        balance=_format_amount(balance),
    )
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
    return False


def _load_history(user_id: int) -> list[dict[str, str]]:
    history = db.get_recent_vexa_assistant_messages(user_id, VEXA_ASSISTANT_HISTORY_LIMIT)
    valid: list[dict[str, str]] = []
    for item in history:
        role = str(item.get("role", "")).strip()
        content = item.get("content")
        if role and content:
            valid.append({"role": role, "content": content})
    return valid


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


def _extract_image_data(bot, message: Message) -> str:
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
    return data_url


def _respond(bot, status_message: Message, lang: str, text: str) -> None:
    safe_text = text if ("<" in text or ">" in text) else html.escape(text)
    try:
        bot.edit_message_text(
            safe_text,
            chat_id=status_message.chat.id,
            message_id=status_message.message_id,
            reply_markup=_chat_keyboard(lang),
            parse_mode="HTML",
        )
    except Exception:
        bot.send_message(
            status_message.chat.id,
            safe_text,
            reply_markup=_chat_keyboard(lang),
            parse_mode="HTML",
        )


def _start_session(bot, chat_id: int, message_id: int, user_id: int, lang: str) -> bool:
    error = _ensure_ready(lang)
    if error:
        edit_or_send(bot, chat_id, message_id, error, _back_keyboard(lang))
        return False

    db.set_state(user_id, STATE)
    db.clear_vexa_assistant_history(user_id)

    if VEXA_ASSISTANT_MESSAGE_COST > 0:
        intro = t("vexa_assistant_open_paid", lang).format(
            cost=_format_amount(VEXA_ASSISTANT_MESSAGE_COST)
        )
    else:
        intro = t("vexa_assistant_open_free", lang)

    edit_or_send(bot, chat_id, message_id, intro, _chat_keyboard(lang))
    return True


def _finish_session(bot, chat_id: int, message_id: int, user_id: int, lang: str) -> None:
    db.clear_state(user_id)
    db.clear_vexa_assistant_history(user_id)
    text = f"{t('vexa_assistant_end', lang)}\n\n{MAIN(lang)}"
    edit_or_send(bot, chat_id, message_id, text, main_menu(lang))


def register(bot):
    @bot.message_handler(commands=["assistant", "vexaassistant"])
    def open_from_command(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️")
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id, lang):
            return

        _start_session(bot, msg.chat.id, msg.message_id, user["user_id"], lang)

    @bot.message_handler(commands=["stopassistant", "stopvexa", "endassistant"])
    def stop_from_command(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])
        _finish_session(bot, msg.chat.id, msg.message_id, user["user_id"], lang)

    @bot.callback_query_handler(func=lambda c: c.data == "home:vexa_assistant")
    def open_from_menu(cq: CallbackQuery):
        user = db.get_or_create_user(cq.from_user)
        if user.get("banned"):
            bot.answer_callback_query(cq.id, "⛔️")
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        if not _ensure_force_sub(
            bot,
            user["user_id"],
            cq.message.chat.id,
            cq.message.message_id,
            lang,
        ):
            bot.answer_callback_query(cq.id)
            return

        if _start_session(bot, cq.message.chat.id, cq.message.message_id, user["user_id"], lang):
            bot.answer_callback_query(cq.id)
        else:
            bot.answer_callback_query(
                cq.id,
                show_alert=True,
                text=t("vexa_assistant_not_configured", lang),
            )

    def _is_assistant_message(message: Message) -> bool:
        state = db.get_state(message.from_user.id) or ""
        return state.startswith("vexa_assistant:")

    @bot.message_handler(func=_is_assistant_message, content_types=["text"])
    def handle_text(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️")
            return

        text = (msg.text or "").strip()
        if not text:
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        error = _ensure_ready(lang)
        if error:
            bot.reply_to(msg, error, parse_mode="HTML")
            db.clear_state(user["user_id"])
            return

        if not _charge_for_message(
            bot,
            user["user_id"],
            msg.chat.id,
            lang,
            VEXA_ASSISTANT_MESSAGE_COST,
        ):
            return

        history = _load_history(user["user_id"])
        history.append({"role": "user", "content": text})
        db.log_vexa_assistant_message(user["user_id"], "user", text)

        thinking = bot.send_message(msg.chat.id, t("vexa_assistant_wait", lang), parse_mode="HTML")
        try:
            answer = request_response(history)
        except VexaAssistantError as exc:
            error_text = t("vexa_assistant_error", lang).format(
                error=html.escape(str(exc))
            )
            _respond(bot, thinking, lang, error_text)
            return

        if not answer:
            answer = t("vexa_assistant_empty", lang)

        db.log_vexa_assistant_message(user["user_id"], "assistant", answer)
        _respond(bot, thinking, lang, answer)

    @bot.message_handler(func=_is_assistant_message, content_types=["photo", "document"])
    def handle_image(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️")
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        error = _ensure_ready(lang)
        if error:
            bot.reply_to(msg, error, parse_mode="HTML")
            db.clear_state(user["user_id"])
            return

        try:
            image_url = _extract_image_data(bot, msg)
        except ValueError:
            bot.reply_to(msg, t("gpt_image_unsupported", lang), parse_mode="HTML")
            return
        except Exception:
            bot.reply_to(msg, t("gpt_image_download_error", lang), parse_mode="HTML")
            return

        if not _charge_for_message(
            bot,
            user["user_id"],
            msg.chat.id,
            lang,
            VEXA_ASSISTANT_MESSAGE_COST,
        ):
            return

        instructions = (msg.caption or "").strip() or t("gpt_image_default_prompt", lang)

        history = _load_history(user["user_id"])
        history.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": instructions},
                    {"type": "input_image", "image_url": {"url": image_url}},
                ],
            }
        )

        db.log_vexa_assistant_message(user["user_id"], "user", f"[image] {instructions}")

        thinking = bot.send_message(msg.chat.id, t("vexa_assistant_wait", lang), parse_mode="HTML")
        try:
            answer = request_response(history)
        except VexaAssistantError as exc:
            error_text = t("vexa_assistant_error", lang).format(
                error=html.escape(str(exc))
            )
            _respond(bot, thinking, lang, error_text)
            return

        if not answer:
            answer = t("vexa_assistant_empty", lang)

        db.log_vexa_assistant_message(user["user_id"], "assistant", answer)
        _respond(bot, thinking, lang, answer)
