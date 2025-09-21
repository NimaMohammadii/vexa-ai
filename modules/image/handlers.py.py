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

def open_image(bot: TeleBot, cq: CallbackQuery) -> None:
    """Display the image generation menu and ask the user for a prompt."""

    user = db.get_or_create_user(cq.from_user)
    user_id = user["user_id"]
    lang = db.get_user_lang(user_id, "fa")
    chat_id = cq.message.chat.id
    message_id = cq.message.message_id

    db.clear_state(user_id)

    if not is_configured():
        edit_or_send(bot, chat_id, message_id, not_configured(lang), menu_keyboard(lang))
        return

    credits = int(user.get("credits") or 0)
    if credits < CREDIT_COST:
        edit_or_send(
            bot,
            chat_id,
            message_id,
            no_credit_text(lang, credits),
            no_credit_keyboard(lang),
        )
        return

    edit_or_send(bot, chat_id, message_id, intro(lang), menu_keyboard(lang))
    _ask_for_prompt(bot, chat_id, reply_to_message_id=message_id)


def _handle_prompt_and_generate(bot: TeleBot, message: Message, prompt_text: str | None = None):
    chat_id = message.chat.id
    _WAITING.pop(chat_id, None)

    user = db.get_or_create_user(message.from_user)
    user_id = user["user_id"]
    lang = db.get_user_lang(user_id, "fa")

    db.clear_state(user_id)

    prompt = (prompt_text or "").strip()
    if not prompt:
        bot.reply_to(message, "❌ متن خالیه. یک توضیح کوتاه بفرست.", parse_mode="HTML")
        return

    if not is_configured():
        bot.reply_to(message, not_configured(lang), parse_mode="HTML")
        return

    if not db.deduct_credits(user_id, CREDIT_COST):
        refreshed = db.get_user(user_id) or {}
        credits = int(refreshed.get("credits") or 0)
        bot.reply_to(
            message,
            no_credit_text(lang, credits),
            reply_markup=no_credit_keyboard(lang),
            parse_mode="HTML",
        )
        return

    refund_needed = True

    try:
        bot.send_chat_action(chat_id, action="upload_photo")
        service = ImageService()
        task_id = service.generate_image(prompt)
        result = service.get_image_status(task_id)
        img = result[0]['image'] if result else None
    except ImageGenerationError as exc:
        if refund_needed:
            db.add_credits(user_id, CREDIT_COST)
        bot.reply_to(
            message,
            f"{error_text(lang)}\n\n{exc}",
            parse_mode="HTML",
        )
        return
    except Exception as exc:  # pragma: no cover - safety net
        if refund_needed:
            db.add_credits(user_id, CREDIT_COST)
        bot.reply_to(
            message,
            f"{error_text(lang)}\n\n{exc}",
            parse_mode="HTML",
        )
        return

    refund_needed = False
    caption_parts = [prompt, "", result_caption(lang)]
    caption = "\n".join(part for part in caption_parts if part).strip()
    bot.send_photo(chat_id, img, caption=caption or None)

def register(bot: TeleBot) -> None:
    # هر callback_data که شامل image یا img باشد را قبول کن
    @bot.callback_query_handler(
        func=lambda c: (c.data or "").lower().startswith("image:")
        or (c.data or "").lower().startswith("img:")
    )
    def on_image_menu(cb: CallbackQuery):
        data = (cb.data or "").lower()
        chat_id = cb.message.chat.id

        if data == "image:back":
            user = db.get_or_create_user(cb.from_user)
            lang = db.get_user_lang(user["user_id"], "fa")
            from modules.home.keyboards import main_menu  # local import to avoid circular
            from modules.home.texts import MAIN

            edit_or_send(bot, chat_id, cb.message.message_id, MAIN(lang), main_menu(lang))
            bot.answer_callback_query(cb.id)
            return

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
            _handle_prompt_and_generate(bot, message, prompt)
        else:
            _ask_for_prompt(bot, message.chat.id, reply_to_message_id=message.message_id)

    # پیام بعدی کاربر وقتی منتظر پرامپت هستیم
    @bot.message_handler(func=lambda m: _WAITING.get(m.chat.id) is True, content_types=["text"])
    def on_prompt_text(message: Message):
        _handle_prompt_and_generate(bot, message, message.text)

    # کمک
    @bot.message_handler(commands=["img_help"])
    def img_help(message: Message):
        bot.reply_to(message, USAGE, parse_mode="HTML")
