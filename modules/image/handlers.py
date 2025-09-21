# modules/image/handlers.py

"""Telegram handlers for the Runway image generation flow"""

from __future__ import annotations

from typing import Any
import logging

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
    intro,
    no_credit as no_credit_text,
    not_configured,
    processing,
    result_caption,
)

logger = logging.getLogger(__name__)

USAGE = (
    "ساخت تصویر از متن:\n"
    "<b>/img</b> متن تصویر\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/img</b>\n"
    "یا از منوی ربات دکمهٔ «تولید تصویر» را بزن."
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

    db.set_state(user["user_id"], STATE_PROCESSING)
    status = bot.send_message(message.chat.id, processing(lang), parse_mode="HTML")

    try:
        task_id = service.generate_image(prompt)
        logger.info(f"Task ID generated: {task_id}")

        result = service.get_image_status(
            task_id, poll_interval=POLL_INTERVAL, timeout=POLL_TIMEOUT
        )
        logger.debug(f"Full result from Runway API: {result}")

        if isinstance(result, dict):
            logger.debug(f"Result keys: {list(result.keys())}")
            if "assets" in result:
                logger.debug(f"Assets content: {result['assets']}")
            if "output" in result:
                logger.debug(f"Output content: {result['output']}")

        image_url = _extract_image_url(result)
        logger.debug(f"Extracted image URL: {image_url}")

        if not image_url:
            logger.error(
                f"No image URL found. Response structure: {str(result)[:500]}..."
            )
            raise ImageGenerationError("خروجی تصویر دریافت نشد.")

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
