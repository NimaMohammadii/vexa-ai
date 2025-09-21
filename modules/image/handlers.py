
# modules/image/handlers.py
"""Telegram handlers for Runway image generation (menu button + /img)."""

from __future__ import annotations

import db
from telebot import TeleBot
from telebot.types import CallbackQuery, ForceReply, Message

from utils import edit_or_send
from .keyboards import menu_keyboard, no_credit_keyboard
from .service import ImageService, ImageGenerationError
from .settings import CREDIT_COST
from .texts import (
    error as error_text,
    intro,
    no_credit as no_credit_text,
    not_configured,
    result_caption,
)

USAGE = (
    "ساخت تصویر از متن:\n"
    "<b>/img</b> متن تصویر\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/img</b>\n"
    "یا از منوی ربات دکمهٔ «تولید تصویر» را بزن."
)

_WAITING: dict[int, bool] = {}

def _extract_prompt(message: Message) -> str:
    text = (message.text or "").strip()
    if text.startswith("/img"):
        parts = text.split(maxsplit=1)
        text = parts[1] if len(parts) > 1 else ""
    if not text and message.reply_to_message:
        text = (message.reply_to_message.text or "").strip()
    return text

def _ask_for_prompt(bot: TeleBot, chat_id: int, reply_to_message_id: int | None = None):
    _WAITING[chat_id] = True
    bot.send_message(
        chat_id,
        "✍️ متن تصویری که می‌خوای تولید بشه رو بفرست",
        reply_to_message_id=reply_to_message_id,
        reply_markup=ForceReply(selective=False),
        parse_mode="HTML",
    )

def open_image(bot: TeleBot, call: CallbackQuery):
    message = call.message
    _ask_for_prompt(bot, message.chat.id, message.message_id)

def handle_img(bot: TeleBot, message: Message):
    user_id = message.from_user.id
    prompt = _extract_prompt(message)

    if not prompt:
        _ask_for_prompt(bot, message.chat.id, message.message_id)
        return

    credits = db.get_credits(user_id)
    if credits < CREDIT_COST:
        bot.send_message(
            message.chat.id,
            no_credit_text,
            reply_markup=no_credit_keyboard(),
            parse_mode="HTML",
        )
        return

    try:
        service = ImageService()
    except ImageGenerationError:
        bot.send_message(message.chat.id, not_configured, parse_mode="HTML")
        return

    status = bot.send_message(message.chat.id, "⏳ در حال تولید تصویر...", parse_mode="HTML")
    try:
        task_id = service.generate_image(prompt)
        result = service.get_image_status(task_id)
        image_url = result[0]['image'] if result else None

        if not image_url:
            raise ImageGenerationError("خروجی تصویر دریافت نشد.")

        bot.send_photo(
            message.chat.id,
            photo=image_url,
            caption=result_caption,
            reply_to_message_id=message.message_id,
            parse_mode="HTML",
        )
        db.decrease_credits(user_id, CREDIT_COST)

    except ImageGenerationError as e:
        bot.edit_message_text(
            f"⚠️ خطا در تولید تصویر:
<code>{str(e)}</code>",
            chat_id=status.chat.id,
            message_id=status.message_id,
            parse_mode="HTML",
        )
