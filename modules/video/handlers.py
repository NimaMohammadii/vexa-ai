"""Telegram handlers for the Runway video generation flow."""

from __future__ import annotations

import logging

import db
from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from modules.home.keyboards import main_menu
from modules.home.texts import MAIN
from modules.i18n import t
from utils import edit_or_send
from .keyboards import menu_keyboard, no_credit_keyboard
from .service import VideoGenerationError, VideoService
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
    "ساخت ویدیو از متن:\n"
    "<b>/video</b> توضیح ویدیو\n"
    "یا روی یک پیام ریپلای کن و بزن: <b>/video</b>\n"
    "یا از منوی ربات دکمهٔ «تولید ویدیو» را بزن."
)


def _extract_prompt(message: Message) -> str:
    text = (message.text or "").strip()
    if text.startswith("/video"):
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


def _process_prompt(bot: TeleBot, message: Message, user, prompt: str, lang: str) -> None:
    prompt = (prompt or "").strip()
    if not prompt:
        _start_prompt_flow(bot, message.chat.id, user["user_id"], lang)
        return

    try:
        service = VideoService()
    except VideoGenerationError:
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
        task_id = service.generate_video(prompt)
        logger.info("Video task created: %s", task_id)

        result = service.get_video_status(
            task_id,
            poll_interval=POLL_INTERVAL,
            timeout=POLL_TIMEOUT,
        )

        video_url = result.get("url")
        if not video_url:
            logger.error("No video URL in result: %s", result)
            raise VideoGenerationError("خروجی ویدیو دریافت نشد.")

        logger.info("Video URL received: %s", video_url[:100])

        kwargs = {
            "caption": result_caption(lang),
            "reply_to_message_id": message.message_id,
            "parse_mode": "HTML",
            "supports_streaming": True,
        }

        bot.send_video(
            message.chat.id,
            video=video_url,
            **kwargs,
        )
        db.deduct_credits(user["user_id"], CREDIT_COST)

        try:
            bot.delete_message(status.chat.id, status.message_id)
        except Exception:
            pass

    except VideoGenerationError as exc:
        logger.error("Video generation error: %s", exc)
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


def open_video(bot: TeleBot, call: CallbackQuery) -> None:
    user, lang = _get_user_and_lang(call.from_user)
    if user.get("banned"):
        bot.answer_callback_query(call.id, t("error_banned", lang), show_alert=True)
        return
    _start_prompt_flow(
        bot, call.message.chat.id, user["user_id"], lang, message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id)


def handle_video(bot: TeleBot, message: Message) -> None:
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
    @bot.callback_query_handler(func=lambda c: c.data == "video:back")
    def on_back(cq: CallbackQuery):
        user, lang = _get_user_and_lang(cq.from_user)
        db.clear_state(user["user_id"])
        edit_or_send(
            bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang)
        )
        bot.answer_callback_query(cq.id)

    @bot.message_handler(commands=["video"])
    def on_video_command(message: Message):
        handle_video(bot, message)

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_PROMPT),
        content_types=["text"],
    )
    def on_prompt(message: Message):
        user, lang = _get_user_and_lang(message.from_user)
        if message.text and message.text.startswith("/"):
            return
        _process_prompt(bot, message, user, message.text or "", lang)
