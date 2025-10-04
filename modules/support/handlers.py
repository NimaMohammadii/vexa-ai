"""Handlers for the support flow."""
from __future__ import annotations

from html import escape

import requests
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import BOT_OWNER_ID, BOT_TOKEN_2
from modules.i18n import t
from utils import edit_or_send
from .keyboards import support_entry_kb, support_chat_kb
from .texts import SUPPORT_INTRO, SUPPORT_PROMPT


STATE_SUPPORT_CHAT = "support:await_message"
STATE_SUPPORT_WAITING = f"{STATE_SUPPORT_CHAT}:waiting"


def _admin_keyboard(user_id: int, include_reply: bool = True) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    if include_reply:
        kb.add(
            InlineKeyboardButton(
                t("support_admin_reply_button", "fa"),
                callback_data=f"support:admin:reply:{user_id}",
            )
        )
    kb.add(
        InlineKeyboardButton(
            t("support_admin_close_button", "fa"),
            callback_data=f"support:admin:end:{user_id}",
        )
    )
    return kb


def _format_username(username: str | None) -> str:
    if username:
        uname = username.strip().lstrip("@")
        if uname:
            return f"@{escape(uname)}"
    return t("support_no_username", "fa")


def _describe_message(msg: Message) -> str:
    content_type = getattr(msg, "content_type", "text")
    if content_type == "text":
        return escape(msg.text or "")

    caption = escape(getattr(msg, "caption", "") or "")
    label = {
        "photo": t("support_type_photo", "fa"),
        "document": t("support_type_document", "fa"),
        "audio": t("support_type_audio", "fa"),
        "voice": t("support_type_voice", "fa"),
        "video": t("support_type_video", "fa"),
        "video_note": t("support_type_video_note", "fa"),
        "sticker": t("support_type_sticker", "fa"),
        "animation": t("support_type_animation", "fa"),
        "contact": t("support_type_contact", "fa"),
        "location": t("support_type_location", "fa"),
    }.get(content_type, content_type)

    if caption:
        return f"{label}\n{t('support_caption', 'fa')}: {caption}"
    return label


def _send_to_admin(bot, user, msg: Message) -> tuple[bool, str]:
    if not BOT_OWNER_ID:
        return False, "not_configured"

    credits = db.format_credit_amount(user.get("credits")) if user else "0"
    first_name = escape((user.get("first_name") or "-") if user else "-")
    username = _format_username(user.get("username") if user else None)
    lang = escape((user.get("lang") or "-") if user else "-")
    info_lines = [
        t("support_admin_header", "fa"),
        "",
        f"🆔 <code>{user.get('user_id')}</code>",
        f"👤 {first_name}",
        f"🔗 {username}",
        f"💳 {t('support_admin_credits', 'fa').format(credits=credits)}",
        f"🌐 {t('support_admin_lang', 'fa').format(lang=lang)}",
        "",
        t("support_admin_message", "fa"),
        _describe_message(msg) or t("support_admin_empty", "fa"),
    ]

    message_text = "\n".join(info_lines)
    markup = _admin_keyboard(user.get("user_id"), include_reply=True)

    error_details = ""
    if BOT_TOKEN_2:
        url = f"https://api.telegram.org/bot{BOT_TOKEN_2}/sendMessage"
        payload = {
            "chat_id": BOT_OWNER_ID,
            "text": message_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            payload["reply_markup"] = markup.to_dict()
        except AttributeError:
            pass
        try:
            response = requests.post(url, json=payload, timeout=15)
            data = (
                response.json()
                if response.headers.get("Content-Type", "").startswith("application/json")
                else {}
            )
            if response.ok and data.get("ok", True):
                return True, ""
            error_details = str(data.get("description") or response.text)
        except Exception as http_exc:  # pragma: no cover - network failures
            error_details = str(http_exc)

    try:
        bot.send_message(
            BOT_OWNER_ID,
            message_text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
        return True, ""
    except Exception as exc:
        if error_details:
            return False, error_details
        return False, str(exc)


def _notify_admin_chat_closed(bot, user: dict | None, closed_by: str) -> None:
    if not BOT_OWNER_ID or not user:
        return

    header_key = (
        "support_admin_chat_closed_by_user"
        if closed_by == "user"
        else "support_admin_chat_closed_by_admin"
    )

    first_name = escape(user.get("first_name") or "-")
    username = _format_username(user.get("username"))
    lines = [
        t(header_key, "fa"),
        "",
        f"🆔 <code>{user.get('user_id')}</code>",
        f"👤 {first_name}",
        f"🔗 {username}",
    ]

    markup = _admin_keyboard(user.get("user_id"), include_reply=(closed_by == "user"))

    if BOT_TOKEN_2:
        url = f"https://api.telegram.org/bot{BOT_TOKEN_2}/sendMessage"
        payload = {
            "chat_id": BOT_OWNER_ID,
            "text": "\n".join(lines),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            payload["reply_markup"] = markup.to_dict()
        except AttributeError:
            pass
        try:
            requests.post(url, json=payload, timeout=15)
            return
        except Exception:  # pragma: no cover - best effort notification
            pass

    try:
        bot.send_message(
            BOT_OWNER_ID,
            "\n".join(lines),
            disable_web_page_preview=True,
            reply_markup=markup,
        )
    except Exception:
        pass


def open_support(bot, cq: CallbackQuery) -> None:
    user = db.get_or_create_user(cq.from_user)
    db.touch_last_seen(user["user_id"])
    lang = db.get_user_lang(user["user_id"], "fa")
    edit_or_send(
        bot,
        cq.message.chat.id,
        cq.message.message_id,
        SUPPORT_INTRO(lang),
        support_entry_kb(lang),
    )


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data in {"support:start", "support:cancel"})
    def support_callbacks(cq: CallbackQuery):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        if cq.data == "support:start":
            if not BOT_TOKEN_2 or not BOT_OWNER_ID:
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    t("support_not_available", lang),
                    support_entry_kb(lang),
                )
                bot.answer_callback_query(cq.id)
                return

            db.set_state(user["user_id"], STATE_SUPPORT_CHAT)
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                SUPPORT_PROMPT(lang),
                support_chat_kb(lang),
            )
            bot.answer_callback_query(cq.id, t("support_started", lang))
            return

        if cq.data == "support:cancel":
            db.clear_state(user["user_id"])
            _notify_admin_chat_closed(bot, user, "user")
            from modules.home.texts import MAIN
            from modules.home.keyboards import main_menu

            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                MAIN(lang),
                main_menu(lang),
            )
            bot.answer_callback_query(cq.id, t("support_cancelled", lang))

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_SUPPORT_CHAT),
        content_types=[
            "text",
            "photo",
            "document",
            "audio",
            "voice",
            "video",
            "video_note",
            "sticker",
            "animation",
            "contact",
            "location",
        ],
    )
    def relay_support_message(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        ok, error = _send_to_admin(bot, user, msg)
        if not ok:
            bot.reply_to(msg, t("support_send_failed", lang))
            if error == "not_configured":
                db.clear_state(user["user_id"])
                from modules.home.texts import MAIN
                from modules.home.keyboards import main_menu

                edit_or_send(
                    bot,
                    msg.chat.id,
                    msg.message_id,
                    t("support_not_available", lang),
                    main_menu(lang),
                )
            return

        db.log_message(user["user_id"], "in", _describe_message(msg))
        state = db.get_state(user["user_id"])
        if state == STATE_SUPPORT_CHAT:
            db.set_state(user["user_id"], STATE_SUPPORT_WAITING)
