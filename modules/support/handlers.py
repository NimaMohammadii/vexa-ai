"""Handlers for the support flow."""
from __future__ import annotations

import io
import threading
from html import escape

import requests
import telebot
from telebot.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import db
from config import BOT_OWNER_ID, BOT_TOKEN_2
from modules.admin.texts import STATE_MSG_TXT
from modules.i18n import t
from utils import edit_or_send
from .keyboards import support_entry_kb, support_chat_kb
from .texts import SUPPORT_INTRO, SUPPORT_PROMPT


STATE_SUPPORT_CHAT = "support:await_message"
STATE_SUPPORT_WAITING = f"{STATE_SUPPORT_CHAT}:waiting"
STATE_ALT_SUPPORT_REPLY = "support:admin_bot:reply"


MAIN_BOT: telebot.TeleBot | None = None
SUPPORT_ADMIN_BOT: telebot.TeleBot | None = None
_ADMIN_BOT_THREAD: threading.Thread | None = None
_ADMIN_THREAD_LOCK = threading.Lock()


def _ensure_admin_bot(main_bot: telebot.TeleBot) -> None:
    """Initialise and start the secondary bot used for admin support."""

    global MAIN_BOT, SUPPORT_ADMIN_BOT, _ADMIN_BOT_THREAD

    if not BOT_TOKEN_2:
        return

    MAIN_BOT = main_bot

    with _ADMIN_THREAD_LOCK:
        if SUPPORT_ADMIN_BOT is not None:
            return

        SUPPORT_ADMIN_BOT = telebot.TeleBot(BOT_TOKEN_2, parse_mode="HTML")
        _register_admin_bot_handlers()

        def _run_admin_bot() -> None:
            try:
                SUPPORT_ADMIN_BOT.infinity_polling(
                    skip_pending=True,
                    allowed_updates=["message", "callback_query"],
                )
            except Exception as exc:  # pragma: no cover - polling loop safety
                print("Support admin bot polling stopped:", exc, flush=True)

        _ADMIN_BOT_THREAD = threading.Thread(
            target=_run_admin_bot,
            name="support-admin-bot",
            daemon=True,
        )
        _ADMIN_BOT_THREAD.start()


def _register_admin_bot_handlers() -> None:
    if SUPPORT_ADMIN_BOT is None:
        return

    bot2 = SUPPORT_ADMIN_BOT

    @bot2.message_handler(commands=["start"])
    def _start(msg: Message) -> None:
        if int(getattr(msg.from_user, "id", 0) or 0) != int(BOT_OWNER_ID or 0):
            bot2.reply_to(msg, "⛔️ مجاز نیستید.")
            return

        bot2.reply_to(msg, t("support_admin_bot_ready", "fa"))

    @bot2.callback_query_handler(func=lambda c: (c.data or "").startswith("support:admin:"))
    def _admin_callbacks(cq: CallbackQuery) -> None:
        if int(getattr(cq.from_user, "id", 0) or 0) != int(BOT_OWNER_ID or 0):
            bot2.answer_callback_query(cq.id, "⛔️")
            return

        parts = (cq.data or "").split(":")
        if len(parts) < 4:
            bot2.answer_callback_query(cq.id, "⚠️")
            return

        action = parts[2]
        try:
            target_uid = int(parts[3])
        except (TypeError, ValueError):
            bot2.answer_callback_query(cq.id, "⚠️")
            return

        user = db.get_user(target_uid)
        if not user:
            bot2.answer_callback_query(cq.id, "❌")
            bot2.send_message(cq.message.chat.id, t("support_admin_reply_not_found", "fa"))
            return

        if action == "reply":
            db.set_state(cq.from_user.id, f"{STATE_ALT_SUPPORT_REPLY}:{target_uid}")
            bot2.answer_callback_query(cq.id, t("support_admin_reply_ready", "fa"))

            first_name = escape(user.get("first_name") or "-")
            username = _format_username(user.get("username"))
            hint_lines = [
                t("support_admin_reply_hint", "fa"),
                "",
                f"🆔 <code>{target_uid}</code>",
                f"👤 {first_name}",
                f"🔗 {username}",
            ]
            bot2.send_message(cq.message.chat.id, "\n".join(hint_lines))
            return

        if action == "end":
            _close_support_chat(target_uid, closed_by="admin")
            bot2.answer_callback_query(cq.id, t("support_admin_closed_chat", "fa"))
            db.clear_state(cq.from_user.id)
            try:
                bot2.edit_message_reply_markup(cq.message.chat.id, cq.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        bot2.answer_callback_query(cq.id, "❓")

    @bot2.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_ALT_SUPPORT_REPLY),
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
    def _handle_admin_reply(msg: Message) -> None:
        if int(getattr(msg.from_user, "id", 0) or 0) != int(BOT_OWNER_ID or 0):
            return

        state = db.get_state(msg.from_user.id) or ""
        try:
            target_uid = int(state.split(":")[-1])
        except (TypeError, ValueError):
            db.clear_state(msg.from_user.id)
            bot2.reply_to(msg, "⚠️ وضعیت نامعتبر.")
            return

        success, error = _relay_admin_message(msg, target_uid)
        if success:
            bot2.reply_to(msg, t("support_admin_reply_sent", "fa"))
        else:
            bot2.reply_to(msg, f"❌ ارسال نشد: {error}")


def _download_admin_file(file_id: str) -> io.BytesIO:
    if not SUPPORT_ADMIN_BOT:
        raise RuntimeError("support admin bot is not initialised")

    file_info = SUPPORT_ADMIN_BOT.get_file(file_id)
    if not file_info or not getattr(file_info, "file_path", ""):
        raise RuntimeError("file not found")

    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN_2}/{file_info.file_path}"
    response = requests.get(file_url, timeout=30)
    response.raise_for_status()

    data = io.BytesIO(response.content)
    filename = file_info.file_path.split("/")[-1] or "file"
    data.name = filename
    data.seek(0)
    return data


def _relay_admin_message(msg: Message, user_id: int) -> tuple[bool, str | None]:
    if MAIN_BOT is None:
        return False, "main bot not ready"

    lang = db.get_user_lang(user_id, "fa")
    reply_markup = support_chat_kb(lang)
    content_type = getattr(msg, "content_type", "text")

    try:
        if content_type == "text":
            text = msg.text or ""
            MAIN_BOT.send_message(user_id, text, reply_markup=reply_markup)
            db.log_message(user_id, "out", text)
            return True, None

        if content_type == "photo" and getattr(msg, "photo", None):
            file_id = msg.photo[-1].file_id
            photo = _download_admin_file(file_id)
            MAIN_BOT.send_photo(user_id, photo, caption=msg.caption or "", reply_markup=reply_markup)
            db.log_message(user_id, "out", msg.caption or "<photo>")
            return True, None

        if content_type == "document" and getattr(msg, "document", None):
            file_id = msg.document.file_id
            document = _download_admin_file(file_id)
            MAIN_BOT.send_document(
                user_id,
                document,
                caption=msg.caption or "",
                reply_markup=reply_markup,
            )
            log_val = msg.caption or f"<document:{getattr(msg.document, 'file_name', '')}>"
            db.log_message(user_id, "out", log_val)
            return True, None

        if content_type == "audio" and getattr(msg, "audio", None):
            file_id = msg.audio.file_id
            audio = _download_admin_file(file_id)
            MAIN_BOT.send_audio(user_id, audio, caption=msg.caption or "", reply_markup=reply_markup)
            db.log_message(user_id, "out", msg.caption or "<audio>")
            return True, None

        if content_type == "voice" and getattr(msg, "voice", None):
            file_id = msg.voice.file_id
            voice = _download_admin_file(file_id)
            MAIN_BOT.send_voice(user_id, voice, caption=msg.caption or "", reply_markup=reply_markup)
            db.log_message(user_id, "out", msg.caption or "<voice>")
            return True, None

        if content_type == "video" and getattr(msg, "video", None):
            file_id = msg.video.file_id
            video = _download_admin_file(file_id)
            MAIN_BOT.send_video(user_id, video, caption=msg.caption or "", reply_markup=reply_markup)
            db.log_message(user_id, "out", msg.caption or "<video>")
            return True, None

        if content_type == "video_note" and getattr(msg, "video_note", None):
            file_id = msg.video_note.file_id
            video_note = _download_admin_file(file_id)
            MAIN_BOT.send_video_note(user_id, video_note, reply_markup=reply_markup)
            db.log_message(user_id, "out", "<video_note>")
            return True, None

        if content_type == "sticker" and getattr(msg, "sticker", None):
            file_id = msg.sticker.file_id
            sticker = _download_admin_file(file_id)
            MAIN_BOT.send_sticker(user_id, sticker)
            db.log_message(user_id, "out", "<sticker>")
            return True, None

        if content_type == "animation" and getattr(msg, "animation", None):
            file_id = msg.animation.file_id
            animation = _download_admin_file(file_id)
            MAIN_BOT.send_animation(user_id, animation, caption=msg.caption or "", reply_markup=reply_markup)
            db.log_message(user_id, "out", msg.caption or "<animation>")
            return True, None

        if content_type == "contact" and getattr(msg, "contact", None):
            contact = msg.contact
            MAIN_BOT.send_contact(
                user_id,
                contact.phone_number,
                contact.first_name,
                last_name=contact.last_name,
                vcard=contact.vcard,
            )
            db.log_message(user_id, "out", "<contact>")
            return True, None

        if content_type == "location" and getattr(msg, "location", None):
            location = msg.location
            MAIN_BOT.send_location(
                user_id,
                location.latitude,
                location.longitude,
            )
            db.log_message(user_id, "out", "<location>")
            return True, None

        return False, "unsupported content"

    except Exception as exc:
        return False, str(exc)


def _close_support_chat(user_id: int, closed_by: str) -> None:
    user = db.get_user(user_id)
    if not user:
        return

    lang = db.get_user_lang(user_id, "fa")
    closing_text = (
        t("support_closed_by_admin", lang)
        if closed_by == "admin"
        else t("support_closed_by_user", lang)
    )

    if MAIN_BOT:
        try:
            MAIN_BOT.send_message(user_id, closing_text)
            db.log_message(user_id, "out", closing_text)
        except Exception:
            pass

        try:
            from modules.home.texts import MAIN as HOME_MAIN
            from modules.home.keyboards import main_menu

            MAIN_BOT.send_message(user_id, HOME_MAIN(lang), reply_markup=main_menu(lang))
        except Exception:
            pass

    db.clear_state(user_id)
    db.clear_support_inbox_for_user(user_id)

MAIN_BOT_USERNAME: str = ""


def _deep_link(action: str, user_id: int) -> str | None:
    username = (MAIN_BOT_USERNAME or "").strip()
    if not username:
        return None
    return f"https://t.me/{username}?start={action}_{user_id}"


def _admin_keyboard(
    user_id: int,
    include_reply: bool = True,
    *,
    use_callback: bool = True,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    if include_reply:
        if use_callback:
            button = InlineKeyboardButton(
                t("support_admin_reply_button", "fa"),
                callback_data=f"support:admin:reply:{user_id}",
            )
        else:
            link = _deep_link("support_reply", user_id)
            button = None
            if link:
                button = InlineKeyboardButton(
                    t("support_admin_reply_button", "fa"),
                    url=link,
                )
        if button:
            kb.add(button)

    if use_callback:
        close_button = InlineKeyboardButton(
            t("support_admin_close_button", "fa"),
            callback_data=f"support:admin:end:{user_id}",
        )
    else:
        link = _deep_link("support_close", user_id)
        close_button = (
            InlineKeyboardButton(
                t("support_admin_close_button", "fa"),
                url=link,
            )
            if link
            else InlineKeyboardButton(
                t("support_admin_close_button", "fa"),
                callback_data=f"support:admin:end:{user_id}",
            )
        )
    kb.add(close_button)
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

    if not BOT_TOKEN_2:
        return False, "not_configured"

    try:
        admin_chat_id = int(BOT_OWNER_ID)
    except (TypeError, ValueError):
        admin_chat_id = BOT_OWNER_ID

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
    callback_markup = _admin_keyboard(user.get("user_id"), include_reply=True)
    use_alt_controls = bool(BOT_TOKEN_2 and MAIN_BOT_USERNAME)
    markup = _admin_keyboard(
        user.get("user_id"),
        include_reply=True,
        use_callback=not use_alt_controls,
    )

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
        if not response.ok or not data.get("ok", True):
            error_details = str(data.get("description") or response.text)
            return False, error_details

        result = data.get("result") or {}
        msg_id = result.get("message_id")
        if msg_id is not None:
    error_details = ""
    info_sent = False

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
                info_sent = True
                result = data.get("result") or {}
                msg_id = result.get("message_id")
                if msg_id is not None:
                    try:
                        db.remember_support_inbox_message(
                            admin_chat_id,
                            int(msg_id),
                            user.get("user_id"),
                            msg.message_id,
                        )
                    except Exception:
                        pass
            else:
                error_details = str(data.get("description") or response.text)
        except Exception as http_exc:  # pragma: no cover - network failures
            error_details = str(http_exc)

    sent_message = None
    if not info_sent:
        try:
            sent_message = bot.send_message(
                BOT_OWNER_ID,
                message_text,
                reply_markup=callback_markup,
                disable_web_page_preview=True,
            )
            info_sent = True
        except Exception as exc:
            if error_details:
                return False, error_details
            return False, str(exc)

    if sent_message is not None:
        chat_id = getattr(getattr(sent_message, "chat", None), "id", admin_chat_id)
        message_id = getattr(sent_message, "message_id", None)
        if message_id is not None:
            try:
                db.remember_support_inbox_message(
                    admin_chat_id,
                    int(msg_id),
                    user.get("user_id"),
                    msg.message_id,
                )
            except Exception:
                pass
    except Exception as http_exc:  # pragma: no cover - network failures
        return False, str(http_exc)

    def _remember_forwarded(forwarded_msg):
        if forwarded_msg is None:
            return
        chat = getattr(forwarded_msg, "chat", None)
        chat_id = getattr(chat, "id", admin_chat_id)
        message_id = getattr(forwarded_msg, "message_id", None)
        if message_id is None:
            try:
                message_id = int(forwarded_msg)
            except Exception:
                message_id = None
        if message_id is None:
            return
        try:
            db.remember_support_inbox_message(
                chat_id,
                message_id,
                user.get("user_id"),
                msg.message_id,
            )
        except Exception:
            pass

    mirror_errors: list[Exception] = []

    if not BOT_TOKEN_2:
        try:
            forwarded = bot.copy_message(admin_chat_id, msg.chat.id, msg.message_id)
            _remember_forwarded(forwarded)
        except Exception as copy_exc:
            mirror_errors.append(copy_exc)
            try:
                forwarded = bot.forward_message(admin_chat_id, msg.chat.id, msg.message_id)
                _remember_forwarded(forwarded)
            except Exception as forward_exc:
                mirror_errors.append(forward_exc)
                if mirror_errors:
                    print("Failed to mirror support message for admin:", mirror_errors, flush=True)

    return True, ""


def _notify_admin_chat_closed(user: dict | None, closed_by: str) -> None:
    if not BOT_OWNER_ID or not user:
        return

    if not BOT_TOKEN_2:
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

    use_alt_controls = bool(BOT_TOKEN_2 and MAIN_BOT_USERNAME)
    markup = _admin_keyboard(
        user.get("user_id"),
        include_reply=(closed_by == "user"),
        use_callback=not use_alt_controls,
    )

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
        bot.send_message(
            BOT_OWNER_ID,
            "\n".join(lines),
            disable_web_page_preview=True,
            reply_markup=_admin_keyboard(
                user.get("user_id"),
                include_reply=(closed_by == "user"),
                use_callback=True,
            ),
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


def handle_admin_deeplink(bot, admin_user, payload: str) -> bool:
    try:
        if int(getattr(admin_user, "id", 0)) != int(BOT_OWNER_ID):
            return False
    except Exception:
        return False

    payload = (payload or "").strip()
    if not payload:
        return False

    lowered = payload.lower()
    if lowered.startswith("support_reply_"):
        target_raw = payload.split("_", 2)[-1]
        try:
            target_uid = int(target_raw)
        except (TypeError, ValueError):
            bot.send_message(admin_user.id, t("support_admin_reply_not_found", "fa"))
            return True

        user = db.get_user(target_uid)
        if not user:
            bot.send_message(admin_user.id, t("support_admin_reply_not_found", "fa"))
            return True

        db.set_state(admin_user.id, f"{STATE_MSG_TXT}:{target_uid}:support:direct")

        first_name = escape(user.get("first_name") or "-")
        username = _format_username(user.get("username"))
        hint_lines = [
            t("support_admin_reply_hint", "fa"),
            "",
            f"🆔 <code>{target_uid}</code>",
            f"👤 {first_name}",
            f"🔗 {username}",
        ]
        bot.send_message(admin_user.id, "\n".join(hint_lines))
        return True

    if lowered.startswith("support_close_"):
        target_raw = payload.split("_", 2)[-1]
        try:
            target_uid = int(target_raw)
        except (TypeError, ValueError):
            bot.send_message(admin_user.id, "⚠️")
            return True

        user = db.get_user(target_uid)
        if not user:
            bot.send_message(admin_user.id, "❌ کاربر یافت نشد.")
            return True

        lang = db.get_user_lang(target_uid, "fa")
        closing_text = t("support_closed_by_admin", lang)
        try:
            bot.send_message(target_uid, closing_text)
            db.log_message(target_uid, "out", closing_text)
        except Exception:
            pass

        db.clear_state(target_uid)
        db.clear_support_inbox_for_user(target_uid)
        try:
            from modules.home.texts import MAIN
            from modules.home.keyboards import main_menu

            bot.send_message(target_uid, MAIN(lang), reply_markup=main_menu(lang))
        except Exception:
            pass

        db.clear_state(admin_user.id)

        first_name = escape(user.get("first_name") or "-")
        username = _format_username(user.get("username"))
        summary_lines = [
            t("support_admin_chat_closed_by_admin", "fa"),
            "",
            f"🆔 <code>{target_uid}</code>",
            f"👤 {first_name}",
            f"🔗 {username}",
        ]
        bot.send_message(admin_user.id, "\n".join(summary_lines))
        return True

    return False


def register(bot):
    _ensure_admin_bot(bot)
    global MAIN_BOT_USERNAME
    if not MAIN_BOT_USERNAME:
        try:
            bot_info = bot.get_me()
            MAIN_BOT_USERNAME = (getattr(bot_info, "username", "") or "").strip()
        except Exception:
            MAIN_BOT_USERNAME = ""
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
            db.clear_support_inbox_for_user(user["user_id"])
            _notify_admin_chat_closed(user, "user")
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
