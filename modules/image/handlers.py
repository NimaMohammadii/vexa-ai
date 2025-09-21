# modules/image/handlers.py
"""Telegram handlers for Runway image generation (menu button + /img)."""

from __future__ import annotations
from telebot import TeleBot
from telebot.types import Message, CallbackQuery, ForceReply

from .service import generate_image, is_configured, ImageGenerationError

USAGE = (
    "ساخت تصویر از متن:\n"
    "<b>/img</b> متن تصویر\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/img</b>\n"
    "یا از منوی ربات دکمهٔ «تولید تصویر» را بزن."
)

# حالت انتظار برای یک چت
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

def _handle_prompt_and_generate(bot: TeleBot, message: Message):
    chat_id = message.chat.id
    prompt = (message.text or "").strip()
    if not prompt:
        bot.reply_to(message, "❌ متن خالیه. یک توضیح کوتاه بفرست.", parse_mode="HTML")
        return
    try:
        bot.send_chat_action(chat_id, action="upload_photo")
        img = generate_image(prompt)
        bot.send_photo(chat_id, img, caption=prompt)
    except ImageGenerationError as e:
        bot.reply_to(message, f"❌ خطا در تولید تصویر:\n{e}", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطای غیرمنتظره:\n{e}", parse_mode="HTML")
    finally:
        _WAITING.pop(chat_id, None)

def register(bot: TeleBot) -> None:
    # هر callback_data که شامل image یا img باشد را قبول کن
    @bot.callback_query_handler(func=lambda c: (c.data or "").lower().find("image") != -1 or (c.data or "").lower().find("img") != -1)
    def on_image_menu(cb: CallbackQuery):
        chat_id = cb.message.chat.id
        if not is_configured():
            bot.answer_callback_query(cb.id, show_alert=True, text="❌ RUNWAY_API ست نشده.")
            return
        bot.answer_callback_query(cb.id)
        _ask_for_prompt(bot, chat_id, reply_to_message_id=cb.message.message_id)

    # دستور /img
    @bot.message_handler(commands=["img", "image", "تصویر"])
    def image_cmd(message: Message):
        if not is_configured():
            bot.reply_to(message, "❌ کلید RUNWAY_API در محیط نیست.", parse_mode="HTML")
            return
        prompt = _extract_prompt(message)
        if prompt:
            _handle_prompt_and_generate(bot, message)
        else:
            _ask_for_prompt(bot, message.chat.id, reply_to_message_id=message.message_id)

    # پیام بعدی کاربر وقتی منتظر پرامپت هستیم
    @bot.message_handler(func=lambda m: _WAITING.get(m.chat.id) is True, content_types=["text"])
    def on_prompt_text(message: Message):
        _handle_prompt_and_generate(bot, message)

    # کمک
    @bot.message_handler(commands=["img_help"])
    def img_help(message: Message):
        bot.reply_to(message, USAGE, parse_mode="HTML")
