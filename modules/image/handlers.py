# modules/image/handlers.py

"""Telegram handlers for the Runway image generation flow"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import logging

import db
from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from modules.home.keyboards import main_menu
from modules.home.texts import MAIN
from modules.i18n import t
from utils import edit_or_send
from ._compat import imghdr
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
    intro,
    invalid_reference,
    no_credit as no_credit_text,
    not_configured,
    processing,
    prompt_required,
    result_caption,
)

logger = logging.getLogger(__name__)

USAGE = (
    "ساخت تصویر از متن:\n"
    "<b>/img</b> متن تصویر\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/img</b>\n"
    "یا از منوی ربات دکمهٔ «تولید تصویر» را بزن.\n\n"
    "بازسازی با عکس مرجع:\n"
    "داخل منو یک عکس با کپشن بفرست یا روی عکس ریپلای کن و بزن: <b>/img توضیح</b>"
)


@dataclass
class _ReferenceImage:
    """Represents a Telegram image attachment that can be used as reference."""

    file_id: str
    mime_type: Optional[str] = None


def _guess_mime_type(data: bytes, fallback: str = "image/jpeg") -> str:
    """Best effort detection of the MIME type for the downloaded reference."""

    detected = imghdr.what(None, h=data)
    if detected:
        if detected == "jpeg":
            return "image/jpeg"
        if detected == "jpg":
            return "image/jpeg"
        return f"image/{detected}"
    return fallback


def _locate_reference_image(message: Message) -> tuple[Optional[_ReferenceImage], bool]:
    """Return the reference image info and whether an invalid file was provided."""

    invalid_attachment = False
    for candidate in filter(None, [message, getattr(message, "reply_to_message", None)]):
        photo_sizes = getattr(candidate, "photo", None)
        if photo_sizes:
            largest = photo_sizes[-1]
            return _ReferenceImage(largest.file_id, "image/jpeg"), False

        document = getattr(candidate, "document", None)
        if document:
            mime = (document.mime_type or "").lower()
            if mime.startswith("image/"):
                return _ReferenceImage(document.file_id, document.mime_type or None), False
            if candidate is message:
                invalid_attachment = True

    if getattr(message, "document", None) and not getattr(message.document, "mime_type", "").lower().startswith("image/"):
        invalid_attachment = True

    return None, invalid_attachment


def _download_reference_image(bot: TeleBot, reference: _ReferenceImage) -> tuple[bytes, str]:
    """Download the reference image from Telegram and detect its MIME type."""

    file_info = bot.get_file(reference.file_id)
    if not file_info:
        raise RuntimeError("FILE_NOT_FOUND")
    data = bot.download_file(file_info.file_path)
    if not data:
        raise RuntimeError("DOWNLOAD_FAILED")

    mime = reference.mime_type or "image/jpeg"
    mime = _guess_mime_type(data, mime)
    return data, mime


def _infer_prompt(initial_prompt: str, message: Message) -> str:
    """Combine the provided prompt with possible captions or replies."""

    prompt = (initial_prompt or "").strip()
    if prompt:
        return prompt

    candidates = [
        getattr(message, "caption", None),
        getattr(message, "text", None),
    ]
    if message.reply_to_message:
        candidates.extend(
            [
                getattr(message.reply_to_message, "caption", None),
                getattr(message.reply_to_message, "text", None),
            ]
        )

    for candidate in candidates:
        if not candidate:
            continue
        cleaned = candidate.strip()
        if cleaned and not cleaned.startswith("/"):
            return cleaned

    return ""


def _extract_prompt(message: Message) -> str:
    text = (message.text or "").strip()
    if text.startswith("/img"):
        parts = text.split(maxsplit=1)
        text = parts[1] if len(parts) > 1 else ""
    if not text and message.reply_to_message:
        text = (message.reply_to_message.text or "").strip()
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


def _send_no_credit(bot: TeleBot, chat_id: int, lang: str, credits: int) -> None:
    bot.send_message(
        chat_id,
        no_credit_text(lang, credits),
        reply_markup=no_credit_keyboard(lang),
        parse_mode="HTML",
    )


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


def _process_prompt(bot: TeleBot, message: Message, user, prompt: str, lang: str) -> None:
    reference, invalid_attachment = _locate_reference_image(message)
    if invalid_attachment:
        bot.reply_to(message, invalid_reference(lang), parse_mode="HTML")
        _start_prompt_flow(
            bot, message.chat.id, user["user_id"], lang, show_intro=False
        )
        return

    prompt = _infer_prompt(prompt, message)
    if not prompt:
        if reference:
            bot.reply_to(message, prompt_required(lang), parse_mode="HTML")
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
    credits = int(fresh.get("credits", 0) or 0)
    if credits < CREDIT_COST:
        _send_no_credit(bot, message.chat.id, lang, credits)
        _start_prompt_flow(
            bot, message.chat.id, user["user_id"], lang, show_intro=False
        )
        return

    reference_payload: tuple[bytes, str] | None = None
    if reference:
        try:
            reference_payload = _download_reference_image(bot, reference)
        except Exception as exc:  # pragma: no cover - depends on Telegram API
            logger.warning("Failed to download reference image", exc_info=exc)
            bot.reply_to(message, invalid_reference(lang), parse_mode="HTML")
            _start_prompt_flow(
                bot, message.chat.id, user["user_id"], lang, show_intro=False
            )
            return

    db.set_state(user["user_id"], STATE_PROCESSING)
    status = bot.send_message(message.chat.id, processing(lang), parse_mode="HTML")

    try:
        # Generate image and get task ID
        reference_image = None
        reference_mime = None
        if reference_payload:
            reference_image, reference_mime = reference_payload
        task_id = service.generate_image(
            prompt,
            reference_image=reference_image,
            reference_mime_type=reference_mime,
        )
        logger.info(f"Image task created: {task_id}")

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
        db.deduct_credits(user["user_id"], CREDIT_COST)

        try:
            bot.delete_message(status.chat.id, status.message_id)
        except Exception:
            pass

    except ImageGenerationError as exc:
        logger.error(f"Image generation error: {exc}")
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
    _process_prompt(bot, message, user, prompt, lang)


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
        if (message.text and message.text.startswith("/")) or (
            message.caption and message.caption.startswith("/")
        ):
            return
        raw_prompt = message.text or message.caption or ""
        _process_prompt(bot, message, user, raw_prompt, lang)
