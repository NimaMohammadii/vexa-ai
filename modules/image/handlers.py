# modules/image/handlers.py
"""Telegram handlers for Runway image generation."""

from __future__ import annotations
from telebot import TeleBot
from telebot.types import Message

from .service import generate_image, is_configured, ImageGenerationError

USAGE = (
    "ساخت تصویر از متن:\n"
    "<b>/img</b> متن تصویر\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/img</b>"
)

def _extract_prompt(message: Message) -> str:
    text = (message.text or "").strip()
    if text.startswith("/img"):
        parts = text.split(maxsplit=1)
        text = parts[1] if len(parts) > 1 else ""
    if not text and message.reply_to_message:
        text = (message.reply_to_message.text or "").strip()
    return text

def register(bot: TeleBot) -> None:
    @bot.message_handler(commands=["img", "image", "تصویر"])
    def image_cmd(message: Message):
        if not is_configured():
            bot.reply_to(message, "❌ کلید Runway پیدا نشد. در ENV یکی از این‌ها را بگذار: RUNWAY_API یا RUNWAY_API_KEY", parse_mode="HTML")
            return

        prompt = _extract_prompt(message)
        if not prompt:
            bot.reply_to(message, USAGE, parse_mode="HTML")
            return

        chat_id = message.chat.id
        try:
            bot.send_chat_action(chat_id, action="upload_photo")
            img = generate_image(prompt)
            bot.send_photo(chat_id, img, caption=prompt)
        except ImageGenerationError as e:
            bot.reply_to(message, f"❌ خطا در تولید تصویر:\n{e}", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"❌ خطای غیرمنتظره:\n{e}", parse_mode="HTML")
