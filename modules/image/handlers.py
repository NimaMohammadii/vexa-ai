# modules/image/handlers.py

"""Telegram handlers for the Runway image generation flow"""

from __future__ import annotations

import html
import logging
import mimetypes
from typing import Any, NamedTuple

import db
from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from modules.home.keyboards import main_menu
from modules.home.texts import MAIN
from modules.i18n import t
from utils import edit_or_send
from .keyboards import menu_keyboard, no_credit_keyboard
from .service import ImageGenerationError, ImageService
from .settings import (
    CREDIT_COST,
    POLL_INTERVAL,
    POLL_TIMEOUT,
    STATE_PROCESSING,
    STATE_WAIT_PROMPT,
)
from .texts import (
    error as error_text,
    invalid_reference,
    intro,
    need_prompt,
    no_credit as no_credit_text,
    not_configured,
    processing,
    reference_download_error,
    result_caption,
)

logger = logging.getLogger(__name__)

USAGE = (
    "ساخت تصویر از متن:\n"
    "<b>/img</b> متن تصویر\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/img</b>\n"
    "یا عکس مرجع + توضیح رو بفرست.\n"
    "یا از منوی ربات دکمهٔ «تولید تصویر» را بزن."
)


def _extract_prompt(message: Message) -> str:
    text = (message.text or message.caption or "").strip()
    if text.startswith("/img"):
        parts = text.split(maxsplit=1)
        text = parts[1] if len(parts) > 1 else ""
    if not text and message.reply_to_message:
        reply = message.reply_to_message
        text = (reply.text or reply.caption or "").strip()
    return text


def _get_user_and_lang(from_user):
    user = db.get_or_create_user(from_user)
    db.touch_last_seen(user["user_id"])
    lang = db.get_user_lang(user["user_id"], "fa")
    return user, lang


def _start_prompt_flow(
    bot: TeleBot,
    chat_id: int,
    user_id: int,
    lang: str,
    *,
    message_id: int | None = None,
    show_intro: bool = True,
) -> None:
    db.set_state(user_id, STATE_WAIT_PROMPT)
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


class ReferenceImage(NamedTuple):
    data: bytes
    mime_type: str | None = None


def _guess_mime_type(file_path: str, fallback: str = "image/jpeg") -> str:
    mime, _ = mimetypes.guess_type(file_path)
    return mime or fallback


def _download_file(bot: TeleBot, file_id: str) -> tuple[bytes, str | None]:
    """Download a Telegram file and return its content and path."""

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
        # ``download_file_by_id`` works for photos even when Telegram
        # generates a temporary path without an extension. Some bot instances
        # run on library versions that do not expose this helper, so guard the
        # call and swallow transport errors. This prevents an AttributeError
        # bubbling up and breaking the handler without giving feedback to the
        # user.
        download_by_id = getattr(bot, "download_file_by_id", None)
        if callable(download_by_id):
            try:
                content = download_by_id(file_id)
            except Exception:
                content = None

    if not content:
        raise RuntimeError("empty file content")

    return content, file_path


def _get_reference_image(bot: TeleBot, message: Message, lang: str, *, _depth: int = 0) -> ReferenceImage | None:
    if message is None or _depth > 2:
        return None

    try:
        if message.photo:
            photo = message.photo[-1]
            content, file_path = _download_file(bot, photo.file_id)
            guessed = _guess_mime_type(file_path or "")
            return ReferenceImage(content, guessed)

        document = getattr(message, "document", None)
        if document:
            mime_type = (document.mime_type or "").lower()
            if not mime_type.startswith("image/"):
                raise ImageGenerationError(invalid_reference(lang))
            content, file_path = _download_file(bot, document.file_id)
            guessed_path = _guess_mime_type(file_path or "")
            guessed = document.mime_type or guessed_path
            return ReferenceImage(content, guessed)

    except ImageGenerationError:
        raise
    except Exception as exc:
        logger.exception("Failed to download reference image", exc_info=exc)
        raise ImageGenerationError(reference_download_error(lang)) from exc

    if message.reply_to_message:
        return _get_reference_image(bot, message.reply_to_message, lang, _depth=_depth + 1)

    return None


def _extract_image_url(data: Any, _visited: set[int] | None = None) -> str | None:
    """Extract a usable image URL from the Runway response structure."""
    if _visited is None:
        _visited = set()

    # Guard against recursive cycles
    data_id = id(data)
    if data_id in _visited:
        return None
    _visited.add(data_id)

    if isinstance(data, str):
        candidate = data.strip()
        if any(
            candidate.startswith(prefix)
            for prefix in [
                "http://",
                "https://",
                "data:image",
                "//",
                "ftp://",
                "file://",
            ]
        ):
            return candidate
        return None

    if isinstance(data, dict):
        # Common keys that may contain image URLs
        priority_keys = [
            "url",
            "image_url",
            "output_url",
            "result_url",
            "download_url",
            "file_url",
            "asset_url",
            "src",
            "href",
            "link",
            "path",
            "uri",
            "output",
        ]

        # Check priority keys first
        for key in priority_keys:
            if key in data:
                url = _extract_image_url(data[key], _visited)
                if url:
                    return url

        # Then check other keys
        lower_priority = {k.lower() for k in priority_keys}
        for key, value in data.items():
            if key.lower() not in lower_priority:
                url = _extract_image_url(value, _visited)
                if url:
                    return url
        return None

    if isinstance(data, (list, tuple, set)):
        for item in data:
            url = _extract_image_url(item, _visited)
            if url:
                return url
        return None

    return None


def _process_prompt(
    bot: TeleBot,
    message: Message,
    user,
    prompt: str,
    lang: str,
    *,
    reference: ReferenceImage | None = None,
) -> None:
    prompt = (prompt or "").strip()
    if not prompt:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    try:
        service = ImageService()
    except ImageGenerationError:
        bot.send_message(message.chat.id, not_configured(lang), parse_mode="HTML")
        _start_prompt_flow(
            bot, message.chat.id, user["user_id"], lang, show_intro=False
        )
        return

    fresh = db.get_user(user["user_id"]) or user
    credits = db.normalize_credit_amount(fresh.get("credits", 0))
    if credits < CREDIT_COST:
        _send_no_credit(bot, message.chat.id, lang, credits)
        _start_prompt_flow(
            bot, message.chat.id, user["user_id"], lang, show_intro=False
        )
        return

    db.set_state(user["user_id"], STATE_PROCESSING)
    status = bot.send_message(message.chat.id, processing(lang), parse_mode="HTML")

    try:
        if reference:
            task_id = service.generate_image_from_image(
                prompt,
                reference.data,
                mime_type=reference.mime_type,
            )
            logger.info("Image-to-image task created: %s", task_id)
        else:
            task_id = service.generate_image(prompt)
            logger.info("Image task created: %s", task_id)

        # Poll for completion and get image URL
        result = service.get_image_status(
            task_id,
            poll_interval=POLL_INTERVAL,
            timeout=POLL_TIMEOUT,
        )
        
        image_url = result.get("url")
        if not image_url:
            logger.error(f"No image URL in result: {result}")
            raise ImageGenerationError("خروجی تصویر دریافت نشد.")
        
        logger.info(f"Image URL received: {image_url[:100]}")

        bot.send_photo(
            message.chat.id,
            photo=image_url,
            caption=result_caption(lang),
            reply_to_message_id=message.message_id,
            parse_mode="HTML",
        )
        try:
            db.log_image_generation(user["user_id"], prompt, image_url)
        except Exception:
            logger.exception("Failed to log image generation for user %s", user["user_id"])
        db.deduct_credits(user["user_id"], CREDIT_COST)

        try:
            bot.delete_message(status.chat.id, status.message_id)
        except Exception:
            pass

    except ImageGenerationError as exc:
        logger.error("Image generation error: %s", exc)
        try:
            error_message = html.escape(str(exc))
            body = (
                f"{error_text(lang)}\n<code>{error_message}</code>"
                if error_message
                else error_text(lang)
            )
            bot.edit_message_text(
                body,
                chat_id=status.chat.id,
                message_id=status.message_id,
                parse_mode="HTML",
            )
        except Exception:
            error_message = html.escape(str(exc))
            body = (
                f"{error_text(lang)}\n<code>{error_message}</code>"
                if error_message
                else error_text(lang)
            )
            bot.send_message(
                message.chat.id,
                body,
                parse_mode="HTML",
            )
    finally:
        _start_prompt_flow(
            bot, message.chat.id, user["user_id"], lang, show_intro=False
        )


def open_image(bot: TeleBot, call: CallbackQuery) -> None:
    user, lang = _get_user_and_lang(call.from_user)
    if user.get("banned"):
        bot.answer_callback_query(call.id, t("error_banned", lang), show_alert=True)
        return
    _start_prompt_flow(
        bot, call.message.chat.id, user["user_id"], lang, message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id)


def handle_img(bot: TeleBot, message: Message) -> None:
    user, lang = _get_user_and_lang(message.from_user)
    if user.get("banned"):
        bot.reply_to(message, t("error_banned", lang))
        return

    prompt = _extract_prompt(message)
    try:
        reference = _get_reference_image(bot, message, lang)
    except ImageGenerationError as exc:
        bot.reply_to(message, str(exc), parse_mode="HTML")
        return

    if reference and not prompt:
        bot.reply_to(message, need_prompt(lang), parse_mode="HTML")
        return

    if not prompt:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    _process_prompt(bot, message, user, prompt, lang, reference=reference)


def register(bot: TeleBot) -> None:
    @bot.callback_query_handler(func=lambda c: c.data == "image:back")
    def on_back(cq: CallbackQuery):
        user, lang = _get_user_and_lang(cq.from_user)
        db.clear_state(user["user_id"])
        edit_or_send(
            bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang)
        )
        bot.answer_callback_query(cq.id)

    @bot.message_handler(commands=["img"])
    def on_img_command(message: Message):
        handle_img(bot, message)

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_PROMPT),
        content_types=["text", "photo", "document"],
    )
    def on_prompt(message: Message):
        user, lang = _get_user_and_lang(message.from_user)

        if message.content_type == "text":
            if message.text and message.text.startswith("/"):
                return
            try:
                reference = _get_reference_image(bot, message, lang)
            except ImageGenerationError as exc:
                bot.reply_to(message, str(exc), parse_mode="HTML")
                return

            text_prompt = message.text or ""
            if reference and not text_prompt.strip():
                bot.reply_to(message, need_prompt(lang), parse_mode="HTML")
                return

            _process_prompt(
                bot,
                message,
                user,
                text_prompt,
                lang,
                reference=reference,
            )
            return

        caption = message.caption or ""
        if caption.startswith("/"):
            return

        try:
            reference = _get_reference_image(bot, message, lang)
        except ImageGenerationError as exc:
            bot.reply_to(message, str(exc), parse_mode="HTML")
            return

        if not reference:
            bot.reply_to(message, invalid_reference(lang), parse_mode="HTML")
            return

        prompt = _extract_prompt(message)
        if not prompt:
            bot.reply_to(message, need_prompt(lang), parse_mode="HTML")
            return

        _process_prompt(
            bot,
            message,
            user,
            prompt,
            lang,
            reference=reference,
        )
