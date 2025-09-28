# modules/image/handlers.py

"""Telegram handlers for the Runway image generation flow"""

from __future__ import annotations

from typing import Any, Dict
import logging
import mimetypes
import os

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
    STATE_WAIT_BLEND_PROMPT,
    STATE_WAIT_IMAGE_ACTION,
    STATE_WAIT_PROMPT,
)
from .texts import (
    error as error_text,
    first_photo_received,
    intro,
    need_blend_prompt,
    need_edit_prompt,
    no_credit as no_credit_text,
    not_configured,
    processing,
    processing_blend,
    processing_edit,
    result_caption,
)

logger = logging.getLogger(__name__)

USAGE = (
    "ساخت تصویر از متن:\n"
    "<b>/img</b> متن تصویر\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/img</b>\n"
    "یا از منوی ربات دکمهٔ «تولید تصویر» را بزن."
)


_IMAGE_STORAGE_ATTR = "temp_image_jobs"


def _get_image_storage(bot: TeleBot) -> Dict[int, Dict[str, Any]]:
    storage = getattr(bot, _IMAGE_STORAGE_ATTR, None)
    if storage is None:
        storage = {}
        setattr(bot, _IMAGE_STORAGE_ATTR, storage)
    return storage


def _store_image_context(bot: TeleBot, user_id: int, context: Dict[str, Any]) -> None:
    storage = _get_image_storage(bot)
    storage[user_id] = context


def _get_image_context(bot: TeleBot, user_id: int) -> Dict[str, Any] | None:
    storage = _get_image_storage(bot)
    return storage.get(user_id)


def _pop_image_context(bot: TeleBot, user_id: int) -> Dict[str, Any] | None:
    storage = _get_image_storage(bot)
    return storage.pop(user_id, None)


def _clear_image_context(bot: TeleBot, user_id: int) -> None:
    storage = _get_image_storage(bot)
    storage.pop(user_id, None)


def _download_image_payload(bot: TeleBot, message: Message) -> Dict[str, Any] | None:
    """Download the referenced Telegram image and return metadata."""

    file_id = None
    filename = ""
    mime_type = ""

    if message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        mime_type = "image/jpeg"
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        file_id = message.document.file_id
        filename = message.document.file_name or ""
        mime_type = message.document.mime_type or ""
    else:
        return None

    try:
        fi = bot.get_file(file_id)
        content = bot.download_file(fi.file_path)
    except Exception:
        return None

    if not filename:
        filename = os.path.basename(fi.file_path or "") or f"{file_id}.jpg"

    if not mime_type:
        mime_type = mimetypes.guess_type(filename)[0] or "image/jpeg"

    return {
        "bytes": content,
        "file_id": file_id,
        "filename": filename,
        "mime": mime_type,
    }


def _execute_image_job(
    bot: TeleBot,
    message: Message,
    user,
    prompt: str,
    lang: str,
    *,
    mode: str,
    primary: Dict[str, Any] | None = None,
    secondary: Dict[str, Any] | None = None,
) -> None:
    """Shared execution path for all image operations."""

    user_id = user["user_id"]
    prompt = (prompt or "").strip()

    try:
        service = ImageService()
    except ImageGenerationError:
        bot.send_message(message.chat.id, not_configured(lang), parse_mode="HTML")
        _start_prompt_flow(bot, message.chat.id, user_id, lang, show_intro=False)
        return

    fresh = db.get_user(user_id) or user
    credits = int(fresh.get("credits", 0) or 0)
    if credits < CREDIT_COST:
        _send_no_credit(bot, message.chat.id, lang, credits)
        _start_prompt_flow(bot, message.chat.id, user_id, lang, show_intro=False)
        return

    if mode in {"generate", "edit"} and not prompt:
        _start_prompt_flow(bot, message.chat.id, user_id, lang, show_intro=False)
        return

    progress_text = processing(lang)
    if mode == "edit":
        progress_text = processing_edit(lang)
    elif mode == "blend":
        progress_text = processing_blend(lang)

    db.set_state(user_id, STATE_PROCESSING)
    status = bot.send_message(message.chat.id, progress_text, parse_mode="HTML")

    try:
        if mode == "generate":
            task_id = service.generate_image(prompt)
        elif mode == "edit":
            if not primary:
                raise ImageGenerationError("فایل تصویر برای ویرایش پیدا نشد.")
            task_id = service.edit_image(
                prompt,
                primary.get("bytes"),
                mime_type=primary.get("mime"),
            )
        elif mode == "blend":
            if not primary or not secondary:
                raise ImageGenerationError("برای ترکیب باید دو تصویر معتبر ارسال شود.")
            task_id = service.blend_images(
                primary.get("bytes"),
                secondary.get("bytes"),
                prompt=prompt,
                mime_a=primary.get("mime"),
                mime_b=secondary.get("mime"),
            )
        else:
            raise ImageGenerationError("نوع درخواست تصویر پشتیبانی نمی‌شود.")

        logger.info(f"Image task created: {task_id}")

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
        db.deduct_credits(user_id, CREDIT_COST)

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
            bot, message.chat.id, user_id, lang, show_intro=False
        )


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
    _clear_image_context(bot, user_id)
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
    prompt = (prompt or "").strip()
    if not prompt:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    _execute_image_job(
        bot,
        message,
        user,
        prompt,
        lang,
        mode="generate",
    )


def _handle_wait_image_action_text(
    bot: TeleBot, message: Message, user, lang: str
) -> None:
    context = _get_image_context(bot, user["user_id"])
    if not context or "primary" not in context:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    prompt = (message.text or "").strip()
    if not prompt:
        bot.reply_to(message, need_edit_prompt(lang), parse_mode="HTML")
        return

    stored = _pop_image_context(bot, user["user_id"])
    if not stored or "primary" not in stored:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    _execute_image_job(
        bot,
        message,
        user,
        prompt,
        lang,
        mode="edit",
        primary=stored["primary"],
    )


def _handle_blend_prompt_text(
    bot: TeleBot, message: Message, user, lang: str
) -> None:
    context = _get_image_context(bot, user["user_id"])
    if not context or "primary" not in context or "secondary" not in context:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    prompt = (message.text or "").strip()
    if not prompt:
        bot.reply_to(message, need_blend_prompt(lang), parse_mode="HTML")
        return

    stored = _pop_image_context(bot, user["user_id"])
    if not stored or "primary" not in stored or "secondary" not in stored:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    _execute_image_job(
        bot,
        message,
        user,
        prompt,
        lang,
        mode="blend",
        primary=stored["primary"],
        secondary=stored["secondary"],
    )


def _handle_blend_skip(bot: TeleBot, message: Message, user, lang: str) -> None:
    stored = _pop_image_context(bot, user["user_id"])
    if not stored or "primary" not in stored or "secondary" not in stored:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    _execute_image_job(
        bot,
        message,
        user,
        "",
        lang,
        mode="blend",
        primary=stored["primary"],
        secondary=stored["secondary"],
    )


def _handle_image_message(bot: TeleBot, message: Message, user, lang: str) -> None:
    payload = _download_image_payload(bot, message)
    if not payload:
        bot.reply_to(message, error_text(lang), parse_mode="HTML")
        return

    caption_prompt = (message.caption or "").strip()
    state = db.get_state(user["user_id"]) or ""

    if state == STATE_WAIT_PROMPT:
        if caption_prompt:
            _execute_image_job(
                bot,
                message,
                user,
                caption_prompt,
                lang,
                mode="edit",
                primary=payload,
            )
            return

        _store_image_context(bot, user["user_id"], {"primary": payload})
        db.set_state(user["user_id"], STATE_WAIT_IMAGE_ACTION)
        bot.send_message(message.chat.id, first_photo_received(lang), parse_mode="HTML")
        return

    if state == STATE_WAIT_IMAGE_ACTION:
        context = _get_image_context(bot, user["user_id"])
        if not context or "primary" not in context:
            _store_image_context(bot, user["user_id"], {"primary": payload})
            db.set_state(user["user_id"], STATE_WAIT_IMAGE_ACTION)
            bot.send_message(message.chat.id, first_photo_received(lang), parse_mode="HTML")
            return

        if caption_prompt:
            stored = _pop_image_context(bot, user["user_id"])
            if not stored:
                _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
                return
            _execute_image_job(
                bot,
                message,
                user,
                caption_prompt,
                lang,
                mode="blend",
                primary=stored["primary"],
                secondary=payload,
            )
            return

        _store_image_context(
            bot,
            user["user_id"],
            {"primary": context["primary"], "secondary": payload},
        )
        db.set_state(user["user_id"], STATE_WAIT_BLEND_PROMPT)
        bot.send_message(message.chat.id, need_blend_prompt(lang), parse_mode="HTML")
        return

    if state == STATE_WAIT_BLEND_PROMPT:
        # User decided to restart with a new image
        _store_image_context(bot, user["user_id"], {"primary": payload})
        db.set_state(user["user_id"], STATE_WAIT_IMAGE_ACTION)
        bot.send_message(message.chat.id, first_photo_received(lang), parse_mode="HTML")
        return

    # Fallback: treat as fresh request
    if caption_prompt:
        _execute_image_job(
            bot,
            message,
            user,
            caption_prompt,
            lang,
            mode="edit",
            primary=payload,
        )
    else:
        _store_image_context(bot, user["user_id"], {"primary": payload})
        db.set_state(user["user_id"], STATE_WAIT_IMAGE_ACTION)
        bot.send_message(message.chat.id, first_photo_received(lang), parse_mode="HTML")


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
    if not prompt:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

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
        content_types=["text"],
    )
    def on_prompt(message: Message):
        user, lang = _get_user_and_lang(message.from_user)
        if message.text and message.text.startswith("/"):
            return
        _process_prompt(bot, message, user, message.text or "", lang)

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith("image:"),
        content_types=["photo", "document"],
    )
    def on_image(message: Message):
        user, lang = _get_user_and_lang(message.from_user)
        if user.get("banned"):
            bot.reply_to(message, t("error_banned", lang))
            return
        _handle_image_message(bot, message, user, lang)

    @bot.message_handler(
        func=lambda m: db.get_state(m.from_user.id) == STATE_WAIT_IMAGE_ACTION,
        content_types=["text"],
    )
    def on_edit_text(message: Message):
        if message.text and message.text.startswith("/"):
            return
        user, lang = _get_user_and_lang(message.from_user)
        if user.get("banned"):
            bot.reply_to(message, t("error_banned", lang))
            return
        _handle_wait_image_action_text(bot, message, user, lang)

    @bot.message_handler(
        func=lambda m: db.get_state(m.from_user.id) == STATE_WAIT_BLEND_PROMPT,
        content_types=["text"],
    )
    def on_blend_text(message: Message):
        if message.text and message.text.startswith("/"):
            return
        user, lang = _get_user_and_lang(message.from_user)
        if user.get("banned"):
            bot.reply_to(message, t("error_banned", lang))
            return
        _handle_blend_prompt_text(bot, message, user, lang)

    @bot.message_handler(commands=["skip"])
    def on_skip(message: Message):
        state = db.get_state(message.from_user.id)
        if state != STATE_WAIT_BLEND_PROMPT:
            return
        user, lang = _get_user_and_lang(message.from_user)
        if user.get("banned"):
            bot.reply_to(message, t("error_banned", lang))
            return
        _handle_blend_skip(bot, message, user, lang)
