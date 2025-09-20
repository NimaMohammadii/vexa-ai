# modules/home/handlers.py
from __future__ import annotations

import db
from telebot.types import CallbackQuery, Message

from utils import edit_or_send, check_force_sub
from modules.i18n import t
from .texts import MAIN, HELP
from .keyboards import main_menu, _back_to_home_kb


def _handle_referral(bot, msg: Message, user):
    """Award referral bonus if /start contains a valid ref code."""
    parts = (msg.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return

    ref_code = parts[1].strip()
    if user.get("referred_by"):
        return

    ref_user = db.get_user(int(ref_code)) if ref_code.isdigit() else None
    if not ref_user or ref_user["user_id"] == user["user_id"]:
        return

    try:
        db.set_referred_by(user["user_id"], ref_user["user_id"])
    except Exception:
        pass

    bonus = int(db.get_setting("BONUS_REFERRAL", "30") or 30)
    try:
        db.add_credits(ref_user["user_id"], bonus)
    except Exception:
        pass

    user_lang = db.get_user_lang(user["user_id"], "fa")
    ref_lang = db.get_user_lang(ref_user["user_id"], "fa")
    free_credits = int(db.get_setting("FREE_CREDIT", "80") or 80)
    try:
        bot.send_message(msg.chat.id, t("ref_welcome", user_lang).format(credits=free_credits))
    except Exception:
        pass
    try:
        bot.send_message(ref_user["user_id"], t("ref_notify", ref_lang).format(credits=bonus))
    except Exception:
        pass


def _ensure_force_sub(bot, user_id: int, chat_id: int, message_id: int | None) -> bool:
    settings = db.get_settings()
    mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
    if mode in ("new", "all"):
        ok, txt, kb = check_force_sub(bot, user_id, settings)
        if not ok:
            edit_or_send(bot, chat_id, message_id, txt, kb)
            return False
    return True


def register(bot):
    @bot.message_handler(commands=["start"])
    def start(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        if user.get("banned"):
            bot.reply_to(msg, t("error_banned", lang))
            return

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id):
            return

        _handle_referral(bot, msg, user)
        edit_or_send(bot, msg.chat.id, msg.message_id, MAIN(lang), main_menu(lang))

    @bot.message_handler(commands=["help"])
    def help_cmd(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id):
            return

        edit_or_send(bot, msg.chat.id, msg.message_id, HELP(lang), _back_to_home_kb(lang))

    @bot.message_handler(commands=["menu"])
    def menu_cmd(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id):
            return

        edit_or_send(bot, msg.chat.id, msg.message_id, MAIN(lang), main_menu(lang))

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("home:") and c.data != "home:gpt_chat")
    def home_router(cq: CallbackQuery):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        if not _ensure_force_sub(bot, user["user_id"], cq.message.chat.id, cq.message.message_id):
            bot.answer_callback_query(cq.id)
            return

        route = cq.data.split(":", 1)[1] if ":" in cq.data else ""

        if route in ("", "back"):
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
            bot.answer_callback_query(cq.id)
            return

        if route == "tts":
            bot.answer_callback_query(cq.id)
            from modules.tts.handlers import open_tts

            open_tts(bot, cq)
            return

        if route == "profile":
            bot.answer_callback_query(cq.id)
            from modules.profile.handlers import open_profile

            open_profile(bot, cq)
            return

        if route == "credit":
            bot.answer_callback_query(cq.id)
            from modules.credit.handlers import open_credit

            open_credit(bot, cq)
            return

        if route == "invite":
            bot.answer_callback_query(cq.id)
            from modules.invite.handlers import open_invite

            open_invite(bot, cq)
            return

        if route == "lang":
            bot.answer_callback_query(cq.id)
            from modules.lang.handlers import open_language

            open_language(bot, cq)
            return

        if route == "clone":
            bot.answer_callback_query(cq.id)
            from modules.clone.handlers import open_clone

            open_clone(bot, cq)
            return

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("fs:"))
    def force_sub_handler(cq: CallbackQuery):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        if cq.data == "fs:recheck":
            settings = db.get_settings()
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if ok:
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
                bot.answer_callback_query(cq.id, t("force_sub_confirmed", lang))
            else:
                bot.answer_callback_query(cq.id, t("force_sub_not_joined", lang))
            return

        bot.answer_callback_query(cq.id)
