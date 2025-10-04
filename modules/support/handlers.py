"""Handlers for the support flow."""
from __future__ import annotations

import requests
from html import escape

from telebot.types import CallbackQuery, Message

import db
from config import BOT_OWNER_ID, BOT_TOKEN_2
from modules.i18n import t
from utils import edit_or_send
from .keyboards import support_entry_kb, support_chat_kb
from .texts import SUPPORT_INTRO, SUPPORT_PROMPT


STATE_SUPPORT_CHAT = "support:await_message"


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


def _send_to_admin(user, msg: Message) -> tuple[bool, str]:
    if not BOT_TOKEN_2 or not BOT_OWNER_ID:
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

    url = f"https://api.telegram.org/bot{BOT_TOKEN_2}/sendMessage"
    payload = {
        "chat_id": BOT_OWNER_ID,
        "text": "\n".join(info_lines),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
        if response.ok and data.get("ok", True):
            return True, ""
        return False, str(data.get("description") or response.text)
    except Exception as exc:  # pragma: no cover - network failures
        return False, str(exc)


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
        func=lambda m: (db.get_state(m.from_user.id) or "") == STATE_SUPPORT_CHAT,
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

        ok, error = _send_to_admin(user, msg)
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
        bot.reply_to(msg, t("support_sent", lang))
