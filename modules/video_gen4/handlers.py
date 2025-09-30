"""Telegram handlers for the Runway Gen-4 video flow."""

from __future__ import annotations

import logging
import mimetypes
from typing import Tuple

import db
from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from modules.home.keyboards import main_menu
from modules.home.texts import MAIN
from modules.i18n import t
from utils import edit_or_send
from .keyboards import menu_keyboard, no_credit_keyboard
from .service import VideoGen4Error, VideoGen4Service
from .settings import (
    CREDIT_COST,
    POLL_INTERVAL,
    POLL_TIMEOUT,
    STATE_PROCESSING,
    STATE_WAIT_IMAGE,
)
from .texts import (
    download_error,
    error as error_text,
    intro,
    invalid_file,
    need_image,
    no_credit as no_credit_text,
    not_configured,
    processing,
    result_caption,
)

logger = logging.getLogger(__name__)


def _get_user_and_lang(from_user):
    user = db.get_or_create_user(from_user)
    db.touch_last_seen(user["user_id"])
    lang = db.get_user_lang(user["user_id"], "fa")
    return user, lang


def _start_flow(
    bot: TeleBot,
    chat_id: int,
    user_id: int,
    lang: str,
    *,
    message_id: int | None = None,
    show_intro: bool = True,
) -> None:
    db.set_state(user_id, STATE_WAIT_IMAGE)
    if not show_intro:
        return
    if message_id is not None:
        edit_or_send(bot, chat_id, message_id, intro(lang), menu_keyboard(lang))
    else:
        bot.send_message(
            chat_id,
            intro(lang),
            reply_markup=menu_keyboard(lang),
            parse_mode="HTML",
        )


def _send_no_credit(bot: TeleBot, chat_id: int, lang: str, credits: float) -> None:
    bot.send_message(
        chat_id,
        no_credit_text(lang, credits),
        reply_markup=no_credit_keyboard(lang),
        parse_mode="HTML",
    )


def _guess_mime_type(file_path: str, fallback: str = "image/jpeg") -> str:
    mime, _ = mimetypes.guess_type(file_path)
    return mime or fallback


def _download_file(bot: TeleBot, file_id: str) -> Tuple[bytes, str | None]:
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


def _extract_image(bot: TeleBot, message: Message, lang: str, *, depth: int = 0) -> Tuple[bytes, str | None]:
    if message is None or depth > 2:
        raise VideoGen4Error(need_image(lang))

    try:
        if message.photo:
            photo = message.photo[-1]
            content, file_path = _download_file(bot, photo.file_id)
            return content, _guess_mime_type(file_path or "")

        document = getattr(message, "document", None)
        if document:
            mime_type = (document.mime_type or "").lower()
            if not mime_type.startswith("image/"):
                raise VideoGen4Error(invalid_file(lang))
            content, file_path = _download_file(bot, document.file_id)
            guessed = document.mime_type or _guess_mime_type(file_path or "")
            return content, guessed

    except VideoGen4Error:
        raise
    except Exception as exc:
        logger.exception("Failed to download telegram image", exc_info=exc)
        raise VideoGen4Error(download_error(lang)) from exc

    if message.reply_to_message:
        return _extract_image(bot, message.reply_to_message, lang, depth=depth + 1)

    raise VideoGen4Error(need_image(lang))


def _process_image(bot: TeleBot, message: Message, user, lang: str) -> None:
    try:
        service = VideoGen4Service()
    except VideoGen4Error:
        bot.send_message(message.chat.id, not_configured(lang), parse_mode="HTML")
        _start_flow(bot, message.chat.id, user["user_id"], lang, show_intro=False)
        return

    fresh = db.get_user(user["user_id"]) or user
    credits = db.normalize_credit_amount(fresh.get("credits", 0))
    if credits < CREDIT_COST:
        _send_no_credit(bot, message.chat.id, lang, credits)
        _start_flow(bot, message.chat.id, user["user_id"], lang, show_intro=False)
        return

    try:
        image_bytes, mime_type = _extract_image(bot, message, lang)
    except VideoGen4Error as exc:
        bot.reply_to(message, str(exc), parse_mode="HTML")
        return

    prompt = (message.caption or "").strip()

    db.set_state(user["user_id"], STATE_PROCESSING)
    status = bot.send_message(message.chat.id, processing(lang), parse_mode="HTML")

    try:
        task_id = service.generate_video(image_bytes, mime_type=mime_type, prompt=prompt)
        result = service.get_video_status(
            task_id,
            poll_interval=POLL_INTERVAL,
            timeout=POLL_TIMEOUT,
        )

        video_url = result.get("url")
        if not video_url:
            raise VideoGen4Error("خروجی ویدیو دریافت نشد.")

        bot.send_video(
            message.chat.id,
            video=video_url,
            caption=result_caption(lang),
            reply_to_message_id=message.message_id,
            parse_mode="HTML",
            supports_streaming=True,
        )

        if not db.deduct_credits(user["user_id"], CREDIT_COST):
            logger.warning("Failed to deduct credits after Gen-4 video", extra={"user": user["user_id"]})

        try:
            bot.delete_message(status.chat.id, status.message_id)
        except Exception:
            pass

    except VideoGen4Error as exc:
        logger.error("Gen-4 video error: %s", exc)
        try:
            bot.edit_message_text(
                f"{error_text(lang)}\n<code>{exc}</code>",
                chat_id=status.chat.id,
                message_id=status.message_id,
                parse_mode="HTML",
            )
        except Exception:
            bot.send_message(
                message.chat.id,
                f"{error_text(lang)}\n<code>{exc}</code>",
                parse_mode="HTML",
            )
    finally:
        _start_flow(bot, message.chat.id, user["user_id"], lang, show_intro=False)


def open_video(bot: TeleBot, call: CallbackQuery) -> None:
    user, lang = _get_user_and_lang(call.from_user)
    if user.get("banned"):
        bot.answer_callback_query(call.id, t("error_banned", lang), show_alert=True)
        return
    _start_flow(
        bot,
        call.message.chat.id,
        user["user_id"],
        lang,
        message_id=call.message.message_id,
    )
    bot.answer_callback_query(call.id)


def register(bot: TeleBot) -> None:
    @bot.callback_query_handler(func=lambda c: c.data == "video_gen4:back")
    def on_back(cq: CallbackQuery):
        user, lang = _get_user_and_lang(cq.from_user)
        db.clear_state(user["user_id"])
        edit_or_send(
            bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang)
        )
        bot.answer_callback_query(cq.id)

    @bot.message_handler(commands=["video"])
    def on_video_command(message: Message):
        user, lang = _get_user_and_lang(message.from_user)
        if user.get("banned"):
            bot.reply_to(message, t("error_banned", lang))
            return
        _start_flow(bot, message.chat.id, user["user_id"], lang)

    @bot.message_handler(content_types=["photo", "document"])
    def on_photo(message: Message):
        caption = (message.caption or "").strip()
        state = db.get_state(message.from_user.id) or ""

        has_command = caption.startswith("/video")
        waiting = state.startswith(STATE_WAIT_IMAGE)

        if not (has_command or waiting):
            return

        user, lang = _get_user_and_lang(message.from_user)
        if user.get("banned"):
            bot.reply_to(message, t("error_banned", lang))
            return

        if has_command:
            parts = caption.split(maxsplit=1)
            message.caption = parts[1] if len(parts) > 1 else ""

        _process_image(bot, message, user, lang)

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_IMAGE),
        content_types=["text"],
    )
    def on_waiting_text(message: Message):
        if message.text and message.text.startswith("/"):
            return
        user, lang = _get_user_and_lang(message.from_user)
        bot.reply_to(message, need_image(lang), parse_mode="HTML")
